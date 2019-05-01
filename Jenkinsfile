// Obtain files from source control system.
if (utils.scm_checkout()) return

matrix_os = ["linux-stable"]
matrix_python = ["3.5", "3.6"]
matrix = []

withCredentials([string(
    credentialsId: 'jwql-codecov',
    variable: 'codecov_token')]) {

  for (os in matrix_os) {
    for (python_ver in matrix_python) {
      // Define each build configuration, copying and overriding values as necessary.
      env_py = "py${python_ver}".replace(".", "")
      bc = new BuildConfig()
      bc.nodetype = os
      bc.name = "debug-${os}-${env_py}"
      bc.build_cmds = [
          "conda env update --file=environment${env_py}.yml",
          "pip install codecov pytest-cov",
          "with_env -n jwql python setup.py install"]
      bc0.test_cmds = [
          "with_env -n jwql pytest -s --junitxml=results.xml --cov=./jwql/ --cov-report=xml:coverage.xml",
          "codecov --token=${codecov_token}",
          "mkdir -v reports",
          "mv -v coverage.xml reports/coverage.xml"]
      matrix += bc
    }
  }
  // bc1 = utils.copy(bc0)
  // bc1.build_cmds[0] = "conda install -q -y python=3.5"

  // Iterate over configurations that define the (distibuted) build matrix.
  // Spawn a host of the given nodetype for each combination and run in parallel.
  utils.run(matrix)
}
