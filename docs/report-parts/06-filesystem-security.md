# 6. Filesystem Security

**Trạng thái:** Chưa hoàn thành  
**Mục tiêu:** Root confinement, metadata, binary I/O, atomic upload and locks.  
**Requirement:** RQ-06, RQ-10. **Owner:** C. **Reviewer:** A.  
**Source:** `role-c-week-2.md`, `api-contract.md`.  
**Code:** `common/filesystem_service.py`, `dir_manager.py`, `file_handler.py`.

**Diagram/table:** path resolution and `.part -> os.replace` flow.  
**Test/evidence:** traversal, symlink, prefix collision, ABOR and concurrent APPE logs (TODO).  
**TODO(C):** Chứng minh mọi A command đã đi qua service.  
**DoD:** Old target survives failed upload and all paths/errors are structured.
