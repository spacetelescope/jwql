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

      bc.build_cmds = [
          "conda env update --file=environment${env_py}.yml",
          "pip install codecov pytest-cov",
          "python setup.py install",
          "python setup.py sdist bdist_wheel"]

      bc.test_cmds = [
          "pytest -s --junitxml=results.xml --cov=./jwql/ --cov-report=xml:coverage.xml",
          "sed -i 's/file=\"[^\"]*\"//g;s/line=\"[^\"]*\"//g;s/skips=\"[^\"]*\"//g' results.xml",
          "codecov --token=${codecov_token}",
          "mkdir -v reports",
          "mv -v coverage.xml reports/coverage.xml",
          "twine upload -u '${pypi_username}' -p '${pypi_password}' --repository-url https://upload.pypi.org/legacy/ --skip-existing dist/*"]

      matrix += bc
    }
  }

  utils.run(matrix)
}