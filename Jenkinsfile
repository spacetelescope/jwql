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
    "rm -fr results.xml coverage.xml cov.xml"]
bc0.test_cmds = [
    "with_env -n jwql pytest -s --junitxml=results.xml --cov=./jwql/ --cov-report xml:coverage/coverage.xml",
    "codecov --token=${codecov_token}"]

// bc1 = utils.copy(bc0)
// bc1.build_cmds[0] = "conda install -q -y python=3.5"

// Iterate over configurations that define the (distibuted) build matrix.
// Spawn a host of the given nodetype for each combination and run in parallel.
utils.run([bc0])
}
