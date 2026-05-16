# The C API library
set( LIB_TYPE "STATIC" )
if (BUILD_SHARED_LIBS)
  set( LIB_TYPE "SHARED" )
endif()
add_library(civetweb-c-library ${LIB_TYPE} civetweb.c)
set_target_properties(civetweb-c-library PROPERTIES
  OUTPUT_NAME "civetweb"
  EXPORT_NAME "civetweb"
  VERSION ${CIVETWEB_VERSION}
  SOVERSION ${CIVETWEB_VERSION}
)
if (BUILD_SHARED_LIBS)
  target_compile_definitions(civetweb-c-library PRIVATE CIVETWEB_DLL_EXPORTS INTERFACE CIVETWEB_DLL_IMPORTS)
endif()
target_include_directories(
  civetweb-c-library PUBLIC
  $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>)
install(
  TARGETS civetweb-c-library
  EXPORT ${PROJECT_NAME}-targets
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  COMPONENT civetweb-c-library
  INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES
  ${PROJECT_SOURCE_DIR}/include/civetweb.h
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
  COMPONENT civetweb-c-library)

# Need Windows sockets if available
find_package(WinSock)
if (WINSOCK_FOUND)
  target_link_libraries(civetweb-c-library WINSOCK::WINSOCK)
endif()

# We need threading
find_package(Threads)
target_link_libraries(civetweb-c-library ${CMAKE_THREAD_LIBS_INIT})

# Need the realtime library if we're using timers
find_package(LibRt)
if (CIVETWEB_ENABLE_WEBSOCKETS AND CIVETWEB_ENABLE_LUA AND LIBRT_FOUND)
  target_link_libraries(civetweb-c-library LIBRT::LIBRT)
endif()

# We need to link OpenSSL if not dynamically loading
if (CIVETWEB_ENABLE_SSL)
  if (CIVETWEB_ENABLE_SSL_DYNAMIC_LOADING)
    find_package(LibDl)
    if (LIBDL_FOUND)
      target_link_libraries(civetweb-c-library -ldl)
    endif()
  else()
    find_package(OpenSSL)
    include_directories(${OPENSSL_INCLUDE_DIR})
    message(STATUS "OpenSSL include directory: ${OPENSSL_INCLUDE_DIR}")
    target_link_libraries(civetweb-c-library ${OPENSSL_LIBRARIES})
  endif()
endif()

# If Lua support is needed we build some extra Lua libraries
if (CIVETWEB_ENABLE_LUA)
  # Use system Lua 5.3 via pkg-config
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(LUA REQUIRED lua5.3 IMPORTED_TARGET)
  message(STATUS "Using system Lua ${LUA_VERSION}")

  # Compile bundled Lua extra modules from src/third_party/ as object files
  # and embed them directly into civetweb-c-library (avoids export issues)
  include_directories("${CMAKE_CURRENT_SOURCE_DIR}/third_party")
  add_library(lua-extras-obj OBJECT
    third_party/lfs.c
    third_party/lsqlite3.c
    third_party/LuaXML_lib.c
    third_party/sqlite3.c)
  set_property(TARGET lua-extras-obj PROPERTY POSITION_INDEPENDENT_CODE ON)
  target_include_directories(lua-extras-obj PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/third_party")
  target_compile_definitions(lua-extras-obj PRIVATE _POSIX_C_SOURCE=200809L)
  target_link_libraries(lua-extras-obj PRIVATE PkgConfig::LUA)

  target_sources(civetweb-c-library PRIVATE $<TARGET_OBJECTS:lua-extras-obj>)
  target_link_libraries(civetweb-c-library PkgConfig::LUA)
endif()

if (CIVETWEB_ENABLE_ZLIB)
  find_package(ZLIB)
  include_directories(${ZLIB_INCLUDE_DIRS})
  target_link_libraries(civetweb-c-library ${ZLIB_LIBRARIES})
endif()

if (CIVETWEB_ENABLE_DUKTAPE)
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(DUKTAPE REQUIRED duktape IMPORTED_TARGET)
  message(STATUS "Using system Duktape ${DUKTAPE_VERSION}")
  target_link_libraries(civetweb-c-library PkgConfig::DUKTAPE)
endif()

# The web server executable
if (CIVETWEB_ENABLE_SERVER_EXECUTABLE)
    add_executable(civetweb-c-executable main.c)
    set_target_properties(civetweb-c-executable PROPERTIES
        EXPORT_NAME "server"
        OUTPUT_NAME "civetweb"
    )
    if (CIVETWEB_INSTALL_EXECUTABLE)
        install(
            TARGETS civetweb-c-executable
            EXPORT ${PROJECT_NAME}-targets
            DESTINATION ${CMAKE_INSTALL_BINDIR}
            COMPONENT server)
    endif()
    target_include_directories(
        civetweb-c-executable PUBLIC
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>)
    target_link_libraries(civetweb-c-executable civetweb-c-library)
    if (LIBRT_FOUND)
        target_link_libraries(civetweb-c-executable LIBRT::LIBRT)
    endif()
endif()

if (CIVETWEB_ENABLE_LUA)
  add_library(lua-library third_party/lfs.c third_party/lsqlite3.c third_party/LuaXML_lib.c third_party/sqlite3.c)
  set_target_properties(lua-library PROPERTIES
    OUTPUT_NAME "lua-library"
    VERSION ${CIVETWEB_VERSION}
    SOVERSION ${CIVETWEB_VERSION}
  )
  target_include_directories(
    lua-library PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/third_party>)
  target_compile_definitions(lua-library PRIVATE _POSIX_C_SOURCE=200809L)
  target_link_libraries(lua-library PkgConfig::LUA)
  install(
    TARGETS lua-library
    EXPORT ${PROJECT_NAME}-targets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    COMPONENT lua-library
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
endif()

# The C++ API library
if (CIVETWEB_ENABLE_CXX)
  add_library(civetweb-cpp ${LIB_TYPE} CivetServer.cpp)
  set_target_properties(civetweb-cpp PROPERTIES
    EXPORT_NAME "civetweb-cpp"
    OUTPUT_NAME "civetweb-cpp"
    VERSION ${CIVETWEB_VERSION}
    SOVERSION ${CIVETWEB_VERSION}
  )
  if (BUILD_SHARED_LIBS)
    target_compile_definitions(civetweb-cpp PRIVATE CIVETWEB_CXX_DLL_EXPORTS INTERFACE CIVETWEB_CXX_DLL_IMPORTS)
  endif()
  target_link_libraries(
    civetweb-cpp PUBLIC
	civetweb-c-library)
  target_include_directories(
    civetweb-cpp PUBLIC
    $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>)
  install(
    TARGETS civetweb-cpp
    EXPORT ${PROJECT_NAME}-targets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    COMPONENT civetweb-cpp
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
  install(FILES
    ${PROJECT_SOURCE_DIR}/include/CivetServer.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    COMPONENT civetweb-cpp)
endif()

# Configure lookup behavior in civetweb config

if(LIBDL_FOUND)
  set(LOOKUP_LIBDL TRUE PARENT_SCOPE)
else()
  set(LOOKUP_LIBDL FALSE PARENT_SCOPE)
endif()

if(LIBRT_FOUND)
  set(LOOKUP_LIBRT TRUE PARENT_SCOPE)
else()
  set(LOOKUP_LIBRT FALSE PARENT_SCOPE)
endif()

if(WINSOCK_FOUND)
  set(LOOKUP_WINSOCK TRUE PARENT_SCOPE)
else()
  set(LOOKUP_WINSOCK FALSE PARENT_SCOPE)
endif()
