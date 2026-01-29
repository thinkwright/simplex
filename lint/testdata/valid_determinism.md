# Valid Determinism Spec

A valid Simplex specification demonstrating DETERMINISM landmark
for controlling output consistency.

DATA: HashResult
  hash: string, required, format hex
  algorithm: sha256 | sha512, required
  input_length: positive integer, required

FUNCTION: compute_hash(data, algorithm) → HashResult

DETERMINISM:
  level: strict
  seed: from input hash

RULES:
  - compute cryptographic hash of input data using specified algorithm
  - if algorithm not supported, fail with error
  - return hash as lowercase hexadecimal string

DONE_WHEN:
  - hash is computed correctly for the algorithm
  - same input always produces same hash
  - hash format is valid hexadecimal

EXAMPLES:
  ("hello", sha256) → { hash: "2cf24dba...", algorithm: sha256, input_length: 5 }
  ("hello", sha512) → { hash: "9b71d224...", algorithm: sha512, input_length: 5 }
  ("", sha256) → { hash: "e3b0c442...", algorithm: sha256, input_length: 0 }
  ("hello", md5) → Error: unsupported algorithm

ERRORS:
  - unsupported algorithm → fail with "unsupported algorithm: {algorithm}"
  - empty algorithm → fail with "algorithm required"
  - any unhandled condition → fail with descriptive message
