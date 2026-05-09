%define soname 1
%def_enable ssl
%def_enable zlib
%def_enable lua
%def_enable duktape
%def_with scripting_tests

%define commit 588860e30721bf5453b0440c390865a8e85dcae5
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name: civetweb
Version: 1.16
Release: alt4.git%shortcommit

Summary: Embedded C/C++ web server
License: MIT
Group: Networking/WWW

Url: https://github.com/civetweb/civetweb
Source: %name-%version.tar
Patch0: 0001-use-system-check.patch
Patch1: 0002-use-system-lua-duktape.patch
Patch2: 0003-fix-svace-null-after-deref-and-use-after-free.patch
Patch3: 0004-fix-test-ssl-cert-path-and-init-library.patch
Patch4: 0005-add-lua-duktape-integration-tests.patch

BuildRequires(pre): cmake make gcc-c++
BuildRequires: /proc /dev/pts
BuildRequires: rpm-build-vm iproute2
BuildRequires: ctest libcheck-devel

%if_enabled zlib
BuildRequires: zlib-devel
%endif
%if_enabled ssl
BuildRequires: openssl-devel
%endif
%if_enabled duktape
BuildRequires: libduktape-devel
%endif
%if_enabled lua
BuildRequires: liblua5.3-devel
%endif

%description
Civetweb is an easy to use, powerful, C (C/C++) embeddable web server
with optional CGI, SSL and Lua support.

CivetWeb can be used by developers as a library, to add web server
functionality to an existing application. It can also be used by end
users as a stand-alone web server running on a Windows or Linux PC.
It is available as single executable, no installation is required.

%package devel
Summary: Civetweb C d C++ header files
Group: Development/Other
Requires: lib%name%soname = %EVR

%description devel
Civetweb associated header files

%package -n lib%name%soname
Summary: Civetweb shared library
Group: Development/Other

%description -n lib%name%soname
Civetweb is an easy to use, powerful, C (C/C++) embeddable web server
with optional CGI, SSL and Lua support.

CivetWeb can be used by developers as a library, to add web server
functionality to an existing application. It can also be used by end
users as a stand-alone web server running on a Windows or Linux PC.
It is available as single executable, no installation is required.

This package contains shared libs for Civetweb server.

%prep
%setup
%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1

%build
%cmake . \
    -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=release \
    -DBUILD_CONFIG=rpmbuild \
    -DCIVETWEB_ENABLE_CXX:BOOL=ON \
    -DBUILD_SHARED_LIBS:BOOL=ON \
    -DCIVETWEB_BUILD_TESTING:BOOL=ON \
%if_enabled lua
    -DCIVETWEB_ENABLE_LUA:BOOL=ON \
    -DCIVETWEB_ENABLE_LUA_SHARED:BOOL=ON \
%endif
%if_enabled ssl
    -DCIVETWEB_ENABLE_SSL:BOOL=ON \
    -DCIVETWEB_ENABLE_SSL_DYNAMIC_LOADING:BOOL=OFF \
%endif
%if_enabled zlib
    -DCIVETWEB_ENABLE_ZLIB:BOOL=ON \
%endif
%if_enabled duktape
    -DCIVETWEB_ENABLE_DUKTAPE:BOOL=ON \
%endif
%nil

%cmake_build

%check
# Excluded: minimal-http(s)-client connect to github.com/google.com (external DNS unavailable)
# IPv6 loopback: iproute2 in BuildRequires; ip link set lo up then ::1 becomes reachable
# SSL cert tests fixed: WORKING_DIRECTORY=${CMAKE_SOURCE_DIR} + LOCAL_TEST (patch 0004)
# init-library fixed: NO_SSL_DL (direct OpenSSL linking, no dlopen)
# server-requests needs cgi_test.cgi pre-built (not a CMake target)
# scripting tests (lua-script, duktape-script): enabled by default, skip with --without scripting_tests
mkdir -p output
gcc -o output/cgi_test.cgi unittest/cgi_test.c
cd %_cmake__builddir
%if_with scripting_tests
CTEST_EXCLUDE='test-publicserver-minimal-https?-client|test-publicserver-start-stop-http-server-ipv6'
%else
CTEST_EXCLUDE='test-publicserver-minimal-https?-client|test-publicserver-start-stop-http-server-ipv6|test-publicserver-lua-script|test-publicserver-duktape-script'
%endif
CTEST_OUTPUT_ON_FAILURE=1 ctest -E "$CTEST_EXCLUDE"
vm-run --kvm=cond --sbin \
    "ip link set lo up; cd $PWD && CTEST_OUTPUT_ON_FAILURE=1 ctest -R test-publicserver-start-stop-http-server-ipv6"

%install
%cmake_install
mkdir -p %buildroot%_docdir/civetweb

%files
%_bindir/civetweb
%doc README.md RELEASE_NOTES.md SECURITY.md

%files -n lib%name%soname
%_libdir/libcivetweb.so.%soname.*
%_libdir/libcivetweb-cpp.so.%soname.*
%if_enabled lua
%_libdir/liblua-library.so.%soname.*
%endif

%files -n %name-devel
%_includedir/*.h
%_libdir/cmake/civetweb
%_libdir/libcivetweb.so
%_libdir/libcivetweb-cpp.so
%if_enabled lua
%_libdir/liblua-library.so
%endif
%_pkgconfigdir/*.pc

%changelog
* Sun May 03 2026 Andrey Kuznetcov <morgonf@altlinux.org> 1.16-alt4.git588860e
- Enable Lua 5.3 and Duktape support via system libraries
- Patch src/CMakeLists.txt: replace ExternalProject_Add downloads (luafilesystem,
  luasqlite, luaxml, sqlite, lua) with system lua5.3 (pkg-config) and bundled
  sources from src/third_party/; link system libduktape (pkg-config)
- BuildRequires: liblua5.3-devel libduktape-devel
- mod_duktape.inl already has DUK_VERSION >= 20000L guards (API-compatible with 2.7.0)
- lua-library.so built from bundled lfs/lsqlite3/LuaXML_lib/sqlite3 extras
- Add integration tests for Lua and Duktape scripting engines (patch 0005)
- resources/test_lua.lua: minimal Lua handler (mg.write, HTTP 200)
- resources/test_duktape.ssjs: minimal Duktape handler (conn.write, HTTP 200)
- scripting tests enabled by default; skip with --without scripting_tests

* Sun May 03 2026 Andrey Kuznetcov <morgonf@altlinux.org> 1.16-alt3.git588860e
- Add %%check: 41 unit tests via system libcheck (patch: use system check
  instead of ExternalProject_Add downloading from github)
- BuildRequires: ctest libcheck-devel
- Exclude 9 tests incompatible with hasher environment:
  external-network (http/https client), IPv6 loopback, SSL cert path,
  init-library (feature count depends on build config)

* Sun May 03 2026 Andrey Kuznetcov <morgonf@altlinux.org> 1.16-alt2.git588860e
- Fixed CVE-2025-55763: refactor request handling to disallow chunked
  encoding combined with content-length header
- Fixed CVE-2026-5789: unquoted search path in Windows service installation
  (Windows-only, commit 3c0fb6ad, included in snapshot %shortcommit)
- Updated to upstream git snapshot %shortcommit

* Sun Jul 02 2023 Andrey Kuznetcov <morgonf@altlinux.org> 1.16-alt1
- Initial build for Sisyphus (based on fedora spec)
  + patch CmakeLists.txt to add project version explicitly
