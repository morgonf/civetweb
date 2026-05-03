%define soname 1
%def_enable ssl
%def_enable zlib
%def_disable lua
%def_disable duktape

%define commit 588860e30721bf5453b0440c390865a8e85dcae5
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name: civetweb
Version: 1.16
Release: alt3.git%shortcommit

Summary: Embedded C/C++ web server
License: MIT
Group: Networking/WWW

Url: https://github.com/civetweb/civetweb
Source: %name-%version.tar
Patch0: 0001-use-system-check.patch

BuildRequires(pre): cmake make gcc-c++
BuildRequires: /proc /dev/pts
BuildRequires: ctest libcheck-devel

%if_enabled zlib
BuildRequires: zlib-devel
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
# Skipped tests:
#  - minimal-http(s)-client: require external DNS (github.com/google.com)
#  - start-stop-http-server-ipv6: IPv6 loopback may be unavailable in chroot
#  - init-library: hardcoded feature count depends on build config (Lua/Duktape off)
#  - minimal-https-server, start-stop-https-server, tls-server-client,
#    server-requests, large-file: SSL cert lookup uses ../../resources/ path
#    which does not resolve correctly from cmake build dir
cd %_cmake__builddir
CTEST_OUTPUT_ON_FAILURE=1 \
    ctest -E 'test-publicserver-init-library|test-publicserver-minimal-https?-client|test-publicserver-start-stop-http-server-ipv6|test-publicserver-minimal-https-server|test-publicserver-start-stop-https-server|test-publicserver-tls-server-client|test-publicserver-server-requests|test-publicserver-large-file'

%install
%cmake_install
mkdir -p %buildroot%_docdir/civetweb

%files
%_bindir/civetweb
%doc README.md RELEASE_NOTES.md SECURITY.md

%files -n lib%name%soname
%_libdir/libcivetweb.so.%soname.*
%_libdir/libcivetweb-cpp.so.%soname.*

%files -n %name-devel
%_includedir/*.h
%_libdir/cmake/civetweb
%_libdir/libcivetweb.so
%_libdir/libcivetweb-cpp.so
%_pkgconfigdir/*.pc

%changelog
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
