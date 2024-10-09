# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.7.1] - 2024-10-07
### Fix
- Disable less usefull pylint errors on specific lines.

## [1.7.0] - 2024-10-04
### Changed
- Refactored `migrate_rbd_images` function in `project-migrator`. The change adds a limited ability to specify
  the order of steps in the volume migration procedure: whether to restore the original state of the related VM
  at the end of the procedure, or in the middle, right after creating snapshots of the volumes.

## [1.6.1] - 2024-09-20
### Fix
- Fixed mapping of single flavor, to correct one.

## [1.6.0] - 2024-08-05
### Added
- Added mappin g for csirtmu.* flavors from g1. They are mapped to g2 flavors.

## [1.5.5] - 2024-08-05
### Fixed
- Fixed error when VM for migration have not attached keypair which causes that key_name attribute of server have value 'None' and this causes script to fail while looking for non-existing key named 'None' in destination.

## [1.5.4] - 2024-08-05
### Fixed
- Added extension into .gitlab-ci.yml file to point to correct template inside kb.

## [1.5.3] - 2024-08-05
### Changed
- Changed generate-data-for-cummunication script - added possibility to specify migration date.
- This change is reflected in .gitlab-ci.yml

## [1.5.2] - 2024-07-25
### Fixed
- temporarily disable compute quotas check

## [1.5.1] - 2024-07-25
### Fixed
- destination network creation (when no network / subnet / router exists)

## [1.5.0] - 2024-07-24
### Added
- src / dst project quota comparison in log
### Fixed
- detection of src keypair

## [1.4.3] - 2024-07-24
### Fixed
- fixed mapping of flavor hpc.8core-128ram to correct one c3.8core-120ram instead of c3.8core-128ram

## [1.4.2] - 2024-07-09
### Fixed
- detection of stc to dst network is now reworked to avoid creation of the network when there is mapped one

## [1.4.1] - 2024-07-09
### Changed
- --migrate-also-inactive-servers renamed to --migrate-inactive-servers
- lib.BOOLEAN_CHOICES introduced improve code quality

## [1.4.0] - 2024-07-09
### Added
- Migration of inactive VMs
### Fixed
- --migrate-volume-snapshots argument value correctly recognized
### Changed
- --migrate-also-inactive-servers now gets argument T/F

## [1.3.0] - 2024-07-08
### Added
- Added way how to migrate RBD snapshot entities

## [1.2.5] - 2024-07-03
### Fixed
- Handle situation when group project network is mapped but not existent

## [1.2.4] - 2024-07-02
### Fixed
- Handle situation when source server has no security-groups linked

## [1.2.3] - 2024-06-19
### Fixed
- fix more robust selection of the source cloud keypair (missing assignment)

## [1.2.2] - 2024-06-19
### Fixed
- more robust selection of the source cloud keypair (search with key_name+user_id and then with key_name only)

## [1.2.1] - 2024-06-11
### Fixed
- corrected argument/switch name from --destination-secgroup-entity-name-prefix to --destination-secgroup-name-prefix

## [1.2.0] - 2024-06-11
### Changed
- source and destination entity names now match except security groups where prefix migrated- is kept

## [1.1.3] - 2024-05-31
### Fixed
- assert disabled projects

## [1.1.2] - 2024-05-30
### Fixed
- attach FIP to correct virtual NIC
### Added
- dry-run mode
- command-line debugging with IPython console

## [1.1.1] - 2024-05-30
### Fixed
- assure correct VM NIC order

## [1.1.0] - 2024-05-30
### Added
- support for multiple ports connected to the VMs
- improved logging

## [1.0.0] - 2024-05-28
### Added
- Initial changelog release
