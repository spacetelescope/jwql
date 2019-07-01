// Obtain files from source control system.
if (utils.scm_checkout()) return

matrix_os = ["linux-stable"]
matrix_python = ["3.5", "3.6"]
matrix = []

withCredentials([
  string(credentialsId: 'jwql-codecov', variable: 'codecov_token'),
  usernamePassword(credentialsId:'jwql-pypi', usernameVariable: 'pypi_username', passwordVariable: 'pypi_password')])

{
  for (os in matrix_os) {
    for (python_ver in matrix_python) {

      env_py = "_python_${python_ver}".replace(".", "_")
      bc = new BuildConfig()
      bc.nodetype = os
      bc.name = "debug-${os}-${env_py}"
      bc.conda_packages = ["python=${python_ver}"]

      bc.build_cmds = ["echo ~",
                       "hostname"]


      matrix += bc
    }
  }

  utils.run(matrix)
}