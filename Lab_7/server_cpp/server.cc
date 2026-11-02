#include <grpcpp/grpcpp.h>
#include "file_processor.grpc.pb.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <mutex>
#include <vector>
#include <chrono>
#include <ctime>
#include <cstdlib>
#include <spawn.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>
#include <cerrno>
extern char **environ;
namespace fs = std::filesystem;
using grpc::Status;
using grpc::StatusCode;
using namespace file_processor;
using Stream = grpc::ServerReaderWriter<FileResponse, FileRequest>;
std::mutex log_mutex;

std::string clean(std::string value) {
  for (char &c : value) if (static_cast<unsigned char>(c) < 32 || c == 127) c = ' ';
  return value.substr(0, 2000);
}
void log(const std::string &method, const std::string &file, const Status &status,
         const std::string &detail = "", std::time_t requested_at = 0) {
  std::lock_guard<std::mutex> lock(log_mutex);
  auto now = std::time(nullptr);
  std::tm tm{}; gmtime_r(&now, &tm);
  if (!requested_at) requested_at = now;
  std::tm request_tm{}; gmtime_r(&requested_at, &request_tm);
  const char *path = std::getenv("LOG_PATH");
  std::ostringstream line;
  line << std::put_time(&tm, "%FT%TZ") << " service=" << method
       << " requested_at=" << std::put_time(&request_tm, "%FT%TZ")
       << " file=" << std::quoted(clean(file)) << " status=" << status.error_code()
       << " message=" << std::quoted(status.ok() ? "sucesso" : clean(status.error_message()))
       << " detail=" << std::quoted(clean(detail)) << '\n';
  std::ofstream out(path ? path : "server.log", std::ios::app);
  if (!(out << line.str())) std::cerr << "Falha ao gravar log\n";
  std::cout << line.str() << std::flush;
}
struct TempDir {
  fs::path path;
  TempDir() {
    char pattern[] = "/tmp/lab7-XXXXXX";
    char *p = mkdtemp(pattern);
    if (!p) throw std::runtime_error("Falha ao criar diretorio temporario");
    path = p;
  }
  ~TempDir() { std::error_code ec; fs::remove_all(path, ec); }
};
// Argumentos separados: nenhum nome/parametro do cliente vira comando de shell.
int execute(const std::vector<std::string> &args, const fs::path &capture) {
  std::vector<char*> argv;
  for (const auto &s : args) argv.push_back(const_cast<char*>(s.c_str()));
  argv.push_back(nullptr);
  posix_spawn_file_actions_t actions;
  posix_spawn_file_actions_init(&actions);
  posix_spawn_file_actions_addopen(&actions, STDOUT_FILENO, capture.c_str(), O_WRONLY|O_CREAT|O_TRUNC, 0600);
  posix_spawn_file_actions_adddup2(&actions, STDOUT_FILENO, STDERR_FILENO);
  pid_t pid;
  int rc = posix_spawnp(&pid, argv[0], &actions, nullptr, argv.data(), environ);
  posix_spawn_file_actions_destroy(&actions);
  if (rc) throw std::runtime_error("Falha ao iniciar ferramenta: " + std::to_string(rc));
  int status;
  while (waitpid(pid, &status, 0) < 0) if (errno != EINTR) throw std::runtime_error("waitpid falhou");
  return WIFEXITED(status) ? WEXITSTATUS(status) : 128;
}

class FileProcessorServiceImpl final : public FileProcessorService::Service {
  Status process(grpc::ServerContext *context, Stream *stream, const std::string &method) {
    std::string name, diagnostic;
    const auto requested_at = std::time(nullptr);
    auto finish = [&](Status s) { log(method, name, s, diagnostic, requested_at); return s; };
    try {
      FileRequest req;
      if (!stream->Read(&req) || !req.has_metadata())
        return finish({StatusCode::INVALID_ARGUMENT, "Primeiro bloco deve conter metadata"});
      const auto meta = req.metadata();
      name = meta.file_name();
      if (name.empty() || name.size() > 255 || name.find_first_of("/\\\r\n") != std::string::npos || name.find('\0') != std::string::npos)
        return finish({StatusCode::INVALID_ARGUMENT, "Nome de arquivo invalido"});
      std::string ext = method == "ConvertToTXT" ? "txt" : "pdf";
      if (method == "ConvertImageFormat") {
        ext = meta.output_format();
        if (ext != "png" && ext != "jpg" && ext != "webp")
          return finish({StatusCode::INVALID_ARGUMENT, "Formato permitido: png, jpg ou webp"});
      }
      if (method == "ResizeImage") {
        ext = "png";
        if (meta.width() < 1 || meta.height() < 1 || meta.width() > 8192 || meta.height() > 8192)
          return finish({StatusCode::INVALID_ARGUMENT, "Dimensoes devem estar entre 1 e 8192"});
      }
      TempDir tmp;
      auto input = tmp.path / "input";
      auto output = tmp.path / ("output." + ext);
      std::ofstream upload(input, std::ios::binary);
      size_t bytes = 0;
      while (stream->Read(&req)) {
        if (!req.has_content()) return finish({StatusCode::INVALID_ARGUMENT, "Metadata repetida ou bloco sem payload"});
        bytes += req.content().size();
        if (bytes > 32 * 1024 * 1024) return finish({StatusCode::RESOURCE_EXHAUSTED, "Limite de upload: 32 MiB"});
        upload.write(req.content().data(), req.content().size());
        if (!upload) return finish({StatusCode::INTERNAL, "Falha ao gravar upload"});
      }
      upload.close();
      if (context->IsCancelled()) return finish({StatusCode::CANCELLED, "Cliente cancelou upload"});
      if (!bytes) return finish({StatusCode::INVALID_ARGUMENT, "Arquivo vazio"});
      std::ifstream signature(input, std::ios::binary);
      char header[5]{}; signature.read(header, 5);
      if ((method == "CompressPDF" || method == "ConvertToTXT") && std::string(header, 5) != "%PDF-")
        return finish({StatusCode::INVALID_ARGUMENT, "Conteudo nao e PDF"});
      if (method == "CompressPDF" || method == "ConvertToTXT") {
        int validation = execute({"timeout", "--signal=KILL", "30s", "pdfinfo", input.string()}, tmp.path / "validation.log");
        if (validation) {
          std::ifstream validation_log(tmp.path / "validation.log");
          char details[1800]{}; validation_log.read(details, sizeof(details));
          diagnostic = "pdfinfo exit=" + std::to_string(validation) + " " + std::string(details, validation_log.gcount());
          return finish({validation == 124 || validation == 137 ? StatusCode::DEADLINE_EXCEEDED : StatusCode::INVALID_ARGUMENT, "PDF invalido ou validacao excedeu prazo"});
        }
      }
      std::vector<std::string> args = {"timeout", "--signal=KILL", "30s"};
      if (method == "CompressPDF") {
        std::vector<std::string> cmd = {"gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4", "-dPDFSETTINGS=/ebook", "-dSAFER", "-dNOPAUSE", "-dQUIET", "-dBATCH", "-sOutputFile=" + output.string(), input.string()};
        args.insert(args.end(), cmd.begin(), cmd.end());
      } else if (method == "ConvertToTXT") {
        args.insert(args.end(), {"pdftotext", input.string(), output.string()});
      } else {
        args.insert(args.end(), {"convert", "-limit", "memory", "128MiB", "-limit", "map", "256MiB", input.string() + "[0]"});
        if (method == "ResizeImage") args.insert(args.end(), {"-resize", std::to_string(meta.width()) + "x" + std::to_string(meta.height())});
        args.push_back(output.string());
      }
      int code = execute(args, tmp.path / "tool.log");
      std::ifstream capture(tmp.path / "tool.log");
      char diagnostic_buffer[1800]{}; capture.read(diagnostic_buffer, sizeof(diagnostic_buffer));
      diagnostic = "exit=" + std::to_string(code) + " " + std::string(diagnostic_buffer, capture.gcount());
      if (code == 124 || code == 137) return finish({StatusCode::DEADLINE_EXCEEDED, "Processamento excedeu 30 segundos"});
      if (code) return finish({StatusCode::INVALID_ARGUMENT, "Ferramenta rejeitou o arquivo; consulte server.log"});
      if (context->IsCancelled()) return finish({StatusCode::CANCELLED, "Cliente cancelou processamento"});
      std::ifstream result(output, std::ios::binary);
      if (!result) return finish({StatusCode::INTERNAL, "Ferramenta nao gerou arquivo de saida"});
      FileResponse response;
      response.set_file_name("output." + ext);
      // Cabecalho de resposta tambem permite TXT vazio (PDF sem texto).
      if (!stream->Write(response)) return finish({StatusCode::CANCELLED, "Cliente desconectou"});
      char buffer[65536];
      while (result.read(buffer, sizeof(buffer)) || result.gcount()) {
        response.set_content(buffer, result.gcount());
        if (!stream->Write(response)) return finish({StatusCode::CANCELLED, "Cliente desconectou"});
      }
      if (result.bad()) return finish({StatusCode::INTERNAL, "Falha ao ler resultado"});
      return finish(Status::OK);
    } catch (const std::exception &e) { return finish({StatusCode::INTERNAL, e.what()}); }
  }
public:
  Status Health(grpc::ServerContext*, const HealthRequest*, HealthResponse *out) override {
    out->set_status("SERVING"); log("Health", "", Status::OK); return Status::OK;
  }
  Status CompressPDF(grpc::ServerContext *c, Stream *s) override { return process(c, s, "CompressPDF"); }
  Status ConvertToTXT(grpc::ServerContext *c, Stream *s) override { return process(c, s, "ConvertToTXT"); }
  Status ConvertImageFormat(grpc::ServerContext *c, Stream *s) override { return process(c, s, "ConvertImageFormat"); }
  Status ResizeImage(grpc::ServerContext *c, Stream *s) override { return process(c, s, "ResizeImage"); }
};
int main() {
  FileProcessorServiceImpl service;
  grpc::ServerBuilder builder;
  builder.AddListeningPort("0.0.0.0:50051", grpc::InsecureServerCredentials());
  builder.RegisterService(&service);
  auto server = builder.BuildAndStart();
  if (!server) { std::cerr << "Falha ao iniciar servidor\n"; return 1; }
  std::cout << "Servidor gRPC ouvindo em 0.0.0.0:50051\n" << std::flush;
  server->Wait();
}
