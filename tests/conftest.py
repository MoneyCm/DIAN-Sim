"""Global safety settings for the test suite.

The repository can be configured with a remote production database for local
development.  Pytest must never inherit that connection.
"""

import os


os.environ["DIAN_SIM_TESTING"] = "1"
os.environ["DIAN_SIM_ENV"] = "test"
os.environ.pop("REQUIRE_DATABASE_URL", None)
os.environ.pop("AUTO_MIGRATE_SCHEMA", None)
