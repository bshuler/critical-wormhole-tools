cmake_minimum_required(VERSION 3.10)
project(ngx_http_wormhole_module C)

set(CMAKE_C_STANDARD 99)

# Find Nginx
find_path(NGINX_INCLUDE_DIR
    NAMES nginx.h
    PATHS /usr/include/nginx /usr/local/include/nginx
)

if(NOT NGINX_INCLUDE_DIR)
    message(FATAL_ERROR "Nginx headers not found. Install nginx-devel or compile from source.")
endif()

# Module source files
set(MODULE_SOURCES
    ngx_http_wormhole_module.c
)

# Include directories
include_directories(
    ${NGINX_INCLUDE_DIR}
    ${NGINX_INCLUDE_DIR}/core
    ${NGINX_INCLUDE_DIR}/http
    ${NGINX_INCLUDE_DIR}/http/modules
    ${NGINX_INCLUDE_DIR}/os/unix
    ${NGINX_INCLUDE_DIR}/event
)

# Compiler flags
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Werror")
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -g -O0")
set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -O2")

# Build shared library
add_library(ngx_http_wormhole_module SHARED ${MODULE_SOURCES})

# Installation
install(TARGETS ngx_http_wormhole_module
    LIBRARY DESTINATION /usr/lib/nginx/modules
)

# Print build info
message(STATUS "Nginx include dir: ${NGINX_INCLUDE_DIR}")
message(STATUS "Module will be installed to: /usr/lib/nginx/modules")
