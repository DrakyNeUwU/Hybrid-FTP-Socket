# 1. Introduction

Hybrid FTP separates control and file payload traffic. TCP carries commands and
FTP replies, while UDP carries file bytes through the custom reliable data
transfer (RDT) protocol. The project targets Python 3 on Linux or WSL2.

Roles are separated: A owns TCP command handling, B owns RDT protocol behavior,
and C owns filesystem safety, server lifecycle, CLI/logging, and integration.
The final evidence combines automated tests, end-to-end transfers, and
source/server/client SHA-256 comparisons.
