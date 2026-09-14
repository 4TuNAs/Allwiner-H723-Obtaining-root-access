# Historical session scripts

The files under `session-scripts/` preserve the logic used during the successful H723 rooting session before this repository was prepared for publication.

They are included for audit/history, not as the recommended public interface. In particular:

- the original Secure Storage writer is intentionally hard-coded to the exact test-unit source/candidate hashes;
- the original Secure Storage patcher's `--require-unlock` check verifies the item names but is less strict than the public tool about exact payload values;
- the original fastboot writer is hard-coded to the exact successful patched `init_boot_a` SHA-256.

Use the hardened scripts under `../scripts/` for new work.
