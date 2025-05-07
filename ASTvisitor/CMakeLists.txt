cmake_minimum_required(VERSION 3.30)
project(AST-visitor)

# Package dependencies
find_package(Clang REQUIRED CONFIG)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Main section
add_executable(optarg-parser main.cpp)


# Include clang libs
# Include  /usr/lib/llvm-19/include/clang/ if you want to compile it manually
target_include_directories(optarg-parser PRIVATE ${CLANG_INCLUDE_DIRS})
target_link_libraries(optarg-parser
  PRIVATE
  clangAST
  clangBasic
  clangFrontend
  clangSerialization
  clangTooling
)
