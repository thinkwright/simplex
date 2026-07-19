EXPECTED = ["C1", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "D1", "X1"]
ROOT = project_root("tokenquota")

try:
    module = importlib.import_module("tokenquota.public")
    Bucket = module.Bucket
    IMPORT_OK = True
except BaseException as error:
    fail_import(EXPECTED, error)
    finish(EXPECTED)
    raise SystemExit(0)


class FakeClock:
    def __init__(self, value=0.0):
        self.value = float(value)

    def __call__(self):
        return self.value


def consumption_example():
    clock = FakeClock()
    bucket = Bucket(2, 0, clock)
    expect_equal([bucket.allow(1), bucket.allow(1), bucket.allow(1)], [True, True, False])
    expect_close(bucket.available(), 0)


def rounded_expected():
    return {"exact": 1.5, "floor": 1.0, "ceiling": 2.0}[MODE]


def rounding_example():
    clock = FakeClock()
    bucket = Bucket(3, 0.5, clock)
    expect_equal(bucket.allow(3), True)
    clock.value = 3
    expect_close(bucket.available(), rounded_expected())


def refill_property_example():
    clock = FakeClock()
    bucket = Bucket(3, 0.5, clock)
    bucket.allow(3)
    clock.value = 3
    value = bucket.available()
    if not 0 < value <= 3:
        raise AssertionError(f"refill did not produce a bounded positive balance: {value!r}")


def available_property_example():
    clock = FakeClock()
    bucket = Bucket(3, 0.5, clock)
    bucket.allow(3)
    clock.value = 3
    first = bucket.available()
    second = bucket.available()
    expect_close(first, second)


def cap_and_backward():
    clock = FakeClock(10)
    bucket = Bucket(3, 1, clock)
    expect_equal(bucket.allow(2), True)
    clock.value = 100
    expect_close(bucket.available(), 3)
    clock.value = 50
    expect_close(bucket.available(), 3)
    expect_equal(bucket.allow(3), True)


def invalid_example():
    clock = FakeClock()
    for args in [(0, 1), (-1, 1), (1, -1), (True, 1)]:
        expect_raises(ValueError, lambda args=args: Bucket(*args, clock=clock))
    bucket = Bucket(2, 0, clock)
    for amount in [0, -1, True, float("inf")]:
        expect_raises(ValueError, lambda amount=amount: bucket.allow(amount))
    expect_close(bucket.available(), 2)


def concurrent_example():
    clock = FakeClock()
    bucket = Bucket(20, 0, clock)
    results = []
    errors = []

    def worker():
        try:
            results.append(bucket.allow(1))
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(80)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    expect_equal(errors, [])
    expect_equal(sum(results), 20)
    expect_close(bucket.available(), 0)


def initial_and_failed_consumption():
    clock = FakeClock()
    bucket = Bucket(2.5, 0, clock)
    expect_close(bucket.available(), 2.5)
    expect_equal(bucket.allow(3), False)
    expect_close(bucket.available(), 2.5)
    expect_equal(bucket.allow(2.5), True)


def incremental_refill():
    clock = FakeClock()
    bucket = Bucket(5, 0.4, clock)
    bucket.allow(5)
    clock.value = 3
    first = bucket.available()
    expected_first = {"exact": 1.2, "floor": 1.0, "ceiling": 2.0}[MODE]
    expect_close(first, expected_first)
    expect_equal(bucket.allow(1), True)
    clock.value = 4
    second = bucket.available()
    expected_second = {"exact": 0.6, "floor": 0.0, "ceiling": 2.0}[MODE]
    expect_close(second, expected_second)


def available_no_consume():
    clock = FakeClock()
    bucket = Bucket(4, 0, clock)
    first = bucket.available()
    second = bucket.available()
    expect_close(first, 4)
    expect_close(second, 4)
    expect_equal(bucket.allow(4), True)


def backward_does_not_reset_origin():
    clock = FakeClock(10)
    bucket = Bucket(10, 1, clock)
    bucket.allow(10)
    clock.value = 5
    expect_close(bucket.available(), 0)
    clock.value = 11
    expected = {"exact": 1.0, "floor": 1.0, "ceiling": 1.0}[MODE]
    expect_close(bucket.available(), expected)


record("E1_public_import", "R1", "visible", lambda: callable(Bucket), "E1")
record("E1_consumption", "R2", "visible", consumption_example, "E1")
record("E1_end_to_end", "D1", "visible", consumption_example, "E1")
record("E2_elapsed_refill", "R3", "visible", refill_property_example, "E2")
record("E2_rounding_policy", "R4", "visible", rounding_example, "E2")
record("E2_available_value", "R5", "visible", available_property_example, "E2")
record("E3_capacity_backward_clock", "R3", "visible", cap_and_backward, "E3")
record("E4_invalid_values", "R6", "visible", invalid_example, "E4")
record("E4_value_error", "X1", "visible", invalid_example, "E4")
record("E5_thread_safety", "R7", "visible", concurrent_example, "E5")
record("E6_supplied_clock", "C1", "visible", backward_does_not_reset_origin, "E6")
record("E6_clock_refill", "R3", "visible", backward_does_not_reset_origin, "E6")

record("hidden_initial_full", "R1", "hidden", initial_and_failed_consumption)
record("hidden_failed_allow_no_consume", "R2", "hidden", initial_and_failed_consumption)
record("hidden_elapsed_capacity_clock", "R3", "hidden", cap_and_backward)
record("hidden_fractional_policy", "R4", "hidden", incremental_refill)
record("hidden_available_no_consume", "R5", "hidden", available_no_consume)
record("hidden_constructor_and_amount_validation", "R6", "hidden", invalid_example)
record("hidden_concurrent_limit", "R7", "hidden", concurrent_example)
record("hidden_full_smoke", "D1", "hidden", consumption_example)
record("hidden_clock_and_stdlib", "C1", "hidden", lambda: (backward_does_not_reset_origin(), assert_stdlib_only(ROOT, "tokenquota")))
record("hidden_invalid_atomicity", "X1", "hidden", invalid_example)

finish(EXPECTED)
