Changelog
=========


0.3.0 (2026-10-30)
------------------

### Changed

- Minimum Python version is now 3.13
- Renamed `konnect.curl.abc.RequestProtocol` to `Request` (#19)
- Removed `konnect.curl.requests.Request` (#19)
- Removed "docs" optional extra dependencies; these are in fact development dependencies 
  (#18)
- Changed return of `konnect.curl.certificates.Certificate.fingerprint()` to a hashlib 
  object (#15, #9)

### Added

- New class `konnect.curl.URL` (#11)
- New function `konnect.curl.xxx.get_writer()` (#7, #2)


0.2.5 (2026-09-04)
------------------

### Added

- Alias the return types of .certificates.detect functions and export from .certificates (#12)
    
### Fixed

- Fix CA certificates not being accepted due to not having private keys (#13)


0.2.4 (2026-04-14)
------------------

### Added

- Significant documentation additions and improvements

### Fixed

- Ensure individual request handles are closed when completed


0.2.3 (2026-01-20)
------------------

### Fixed

- Add missing export of `CommonEncodedSource` from .certificates


0.2.2 (2026-01-20)
------------------

### Added

- Add client and CA certificate support, for some backends


0.2.1 (2025-04-15)
------------------

### Fixed

- Fix a timer issue which was causing busy looping
- Fix a socket/file-descriptor issue, possibly affecting C-ares enabled builds of Curl


0.2.0 (2024-12-03)
------------------

### Changed

- Decouple request protocol methods' signatures from Pycurl
- Rename `has_response` and `response` to `has_update` and `get_update` respectively
- Differentiate between the return types of `get_update` (previously `update`) and `completed`
- Use the new, independent `kodo.quantities` package for time quantities
