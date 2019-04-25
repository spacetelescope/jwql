// Obtain files from source control system.
if (utils.scm_checkout()) return

CONDA_CHANNEL = "http://ssb.stsci.edu/astroconda-dev"
CONDA_INST = "conda install -y -q -c ${CONDA_CHANNEL}"

matrix_os = ["linux-stable"]
matrix_python = ["3.5", "3.6"]
matrix = []

withCredentials([string(
    credentialsId: 'jwql-codecov',
    variable: 'codecov_token')]) {

  for (os in matrix_os) {
    for (python_ver in matrix_python) {
      // Define each build configuration, copying and overriding values as necessary.
      bc = new BuildConfig()
      bc.nodetype = os
      bc.name = "debug-os${os}-py${python_ver}"
      bc.build_cmds = [
          "conda env update --file=environment.yml",
          "pip install codecov pytest-cov",
          "with_env -n jwql ${CONDA_INST} python=${python_ver}",
          "with_env -n jwql python setup.py install"]
      bc.test_cmds = [
          "with_env -n jwql pytest -s --junitxml=results.xml --cov=./jwql/ --cov-report xml",
          "codecov --token=${codecov_token}"]
      matrix += bc
    }
  }
  // bc1 = utils.copy(bc0)
  // bc1.build_cmds[0] = "conda install -q -y python=3.5"

  // Iterate over configurations that define the (distibuted) build matrix.
  // Spawn a host of the given nodetype for each combination and run in parallel.
  utils.run(matrix)
}
