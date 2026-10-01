# Redmi K50 Ultra / diting stock-source SukiSU build

Targets OS3.0.3.0.VLFCNXM (Android 15) and the stock kernel commit
fb24cf99ad973cd4c7c7fa375c6053f939ef3a89, Android 12 5.10 KMI generation 9.

Uses the SukiSU/SUSFS/KPM revisions underlying ShirkNeko v2.1.0.
Builds a single Image from the extracted stock configuration, retaining FullLTO,
stock schedutil, energy model, idle, thermal and network configuration.
Only root-related features and the build-path-specific symbol whitelist differ.
Identity is set in source before compilation and checked in the generated Image.
Scheduler, CPU frequency, idle, thermal, OPP and power source files must stay unchanged.

This is a custom source build, not an official Xiaomi or SukiSU release.
Static checks cannot guarantee identical power consumption, vendor module loading,
successful root authorization or absence of root detection. Device testing is required.

AK3 helper programs are obtained from the hash-checked ShirkNeko release template.
Source downloads and checksums, resolved configuration, configuration differences,
protected-source hashes and compiled identity verification are included in artifacts.
