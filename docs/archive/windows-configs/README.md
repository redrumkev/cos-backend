# Archived Windows Configuration Files

This directory contains Windows-specific configuration files that have been archived as the COS project has standardized on macOS development environment.

## Archived Files

### .env.windows
The Windows-specific environment configuration file. Key differences from macOS version:
- **Platform identifier**: `PLATFORM=windows`
- **Data root paths**: Used Windows drive letters for optimal performance
  - `COS_DATA_ROOT=C:/cos-data`
  - `COS_POSTGRES_ROOT=P:/postgres_cos`
  - `COS_REDIS_ROOT=E:/redis_cos_data`
  - `COS_NEO4J_ROOT=F:/neo4j_cos_data`
  - `COS_ELASTICSEARCH_ROOT=F:/elasticsearch_cos_data`

### docker-compose.override.yml.windows
Windows-specific Docker Compose override file with:
- Windows-style volume mappings using drive letters
- Platform-specific path separators

### setup-platform.ps1
PowerShell script for Windows platform setup:
- Created data directories on specific Windows drives
- Configured Windows-specific Docker Desktop settings
- Copied Windows-specific configuration files

## Migration Notes

The project has standardized on macOS development with:
- All environment variables in `.env` (copied from `.env.macos`)
- Unified data directory structure under `~/cos-data/`
- macOS-specific Docker configurations

## Windows Development (Historical)

If Windows development is needed in the future:
1. These configurations would need updating for current project state
2. Consider using WSL2 for better Unix compatibility
3. Update paths to use WSL2 mount points instead of Windows drives

## Archive Date
July 11, 2025
