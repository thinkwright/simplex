# Invalid: Too Complex

This spec exceeds complexity limits.

FUNCTION: overly_complex(a, b, c, d, e, f, g, h) → result

RULES:
  - rule 1: do something
  - rule 2: do something else
  - rule 3: handle case A
  - rule 4: handle case B
  - rule 5: handle case C
  - rule 6: handle case D
  - rule 7: handle case E
  - rule 8: handle case F
  - rule 9: validate input A
  - rule 10: validate input B
  - rule 11: validate input C
  - rule 12: transform step 1
  - rule 13: transform step 2
  - rule 14: transform step 3
  - rule 15: aggregate results
  - rule 16: format output
  - rule 17: this exceeds the default limit of 15

DONE_WHEN:
  - everything is done

EXAMPLES:
  (1, 2, 3, 4, 5, 6, 7, 8) → result

ERRORS:
  - any error → fail
