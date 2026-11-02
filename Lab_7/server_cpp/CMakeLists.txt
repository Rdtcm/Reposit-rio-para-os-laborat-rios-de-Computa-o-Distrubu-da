cmake_minimum_required(VERSION 3.16)
project(file_processor LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(Protobuf REQUIRED)
find_package(gRPC CONFIG REQUIRED)
set(PROTO ${CMAKE_CURRENT_SOURCE_DIR}/../proto/file_processor.proto)
add_custom_command(OUTPUT file_processor.pb.cc file_processor.pb.h file_processor.grpc.pb.cc file_processor.grpc.pb.h
  COMMAND protobuf::protoc --proto_path=${CMAKE_CURRENT_SOURCE_DIR}/../proto
  --cpp_out=${CMAKE_CURRENT_BINARY_DIR} --grpc_out=${CMAKE_CURRENT_BINARY_DIR}
  --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin> ${PROTO}
  DEPENDS ${PROTO})
add_executable(server server.cc ${CMAKE_CURRENT_BINARY_DIR}/file_processor.pb.cc ${CMAKE_CURRENT_BINARY_DIR}/file_processor.grpc.pb.cc)
target_include_directories(server PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(server PRIVATE gRPC::grpc++ protobuf::libprotobuf)
target_compile_options(server PRIVATE -Wall -Wextra -Wpedantic)
