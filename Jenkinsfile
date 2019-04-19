// Obtain files from source control system.
if (utils.scm_checkout()) return

withCredentials([string(
    credentialsId: 'jwql-codecov',
    variable: 'codecov_token')]) {

// Define each build configuration, copying and overriding values as necessary.
bc0 = new BuildConfig()
bc0.nodetype = "linux-stable"
bc0.name = "debug"
bc0.build_cmds = [
    "conda env update --file=environment.yml",
    "pip install codecov pytest-cov",
    "with_env -n jwql python setup.py install",
    "rm -vfr results.xml",
    "rm -vfr coverage.xml"]
bc0.test_cmds = [
    "with_env -n jwql pytest -s --junitxml=results.xml --cov=./jwql/ --cov-report=xml:coverage.xml",
    "codecov --token=${codecov_token}",
    "mkdir -v reports",
    "mv -v coverage.xml reports/coverage.xml"]

// bc1 = utils.copy(bc0)
// bc1.build_cmds[0] = "conda install -q -y python=3.5"

// Iterate over configurations that define the (distibuted) build matrix.
// Spawn a host of the given nodetype for each combination and run in parallel.
utils.run([bc0])
}
