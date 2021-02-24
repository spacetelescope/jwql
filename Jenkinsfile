// JWQL Jenkinsfile
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
//
// Authors:
// --------
// - Matthew Bourque
// - Lauren Chambers
// - Joshua Alexander
// - Sara Ogaz
// - Matt Rendina
//
// Notes:
// ------
// - More info here: https://github.com/spacetelescope/jenkinsfile_ci_examples
// - Syntax defined here: https://github.com/spacetelescope/jenkins_shared_ci_utils
//
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
//
// scm_checkout() does the following:
//     1. Disables pipeline execution if [skip ci] or [ci skip] is present in the
//          commit message, letting users exclude individual commits from CI
//     2. Clones the Git repository
//     3. Creates a local cache of the repository to avoid commit drift between tasks
//        (i.e. Each stage is guaranteed to receive the same source code regardless of
//          commits taking place after the pipeline has started.)
if (utils.scm_checkout()) return

// Establish OS and Python version variables for the matrix
matrix_os = ["linux-stable"] // (Note that Jenkins can only be run with Linux, not MacOSX/Windows)
matrix_python = ["3.7", "3.8"]

// Set up the matrix of builds
matrix = []

// Define IDs that live on the Jenkins server (here, for CodeCov and PyPI)
withCredentials([
    string(credentialsId: 'jwql-codecov', variable: 'codecov_token'),
    usernamePassword(credentialsId:'jwql-pypi', usernameVariable: 'pypi_username', passwordVariable: 'pypi_password')])

// Iterate over the above variables to define the build matrix.
{
    for (os in matrix_os) {
        for (python_ver in matrix_python) {
            // Define each build configuration, copying and overriding values as necessary.

            // Define a string variable to reflect the python version of this build
            env_py = "_python_${python_ver}".replace(".", "_")

            // Create a new build configuration
            bc = new BuildConfig()

            // Define the OS (only "linux-stable" used here)
            bc.nodetype = os

            // Give the build configuration a name. This string becomes the
            // stage header on Jenkins' UI. Keep it short!
            bc.name = "debug-${os}-${env_py}"

            // (Required) Define what packages to include in the base conda environment.
            // This specification also tells Jenkins to spin up a new conda environment for
            // your build, rather than using the default environment.
            bc.conda_packages = ["python=${python_ver}"]

            // Execute a series of commands to set up the build, including
            // any packages that have to be installed with pip
            bc.build_cmds = [
                "conda env update --file=environment${env_py}.yml", // Update env from file
                "pip install codecov pytest-cov", // Install additional packages
                "python setup.py install", // Install JWQL package
                "python setup.py sdist bdist_wheel" // Build JWQL pacakge wheel for PyPI
            ]

            // Execute a series of test commands
            bc.test_cmds = [
                // Run pytest
                "pytest ./jwql/tests/ -s --junitxml=results.xml --cov=./jwql/ --cov-report=xml:coverage.xml",
                // Add a truly magical command that makes Jenkins work for Python 3.5
                "sed -i 's/file=\"[^\"]*\"//g;s/line=\"[^\"]*\"//g;s/skips=\"[^\"]*\"//g' results.xml",
                // Define CodeCov token
                "codecov --token=${codecov_token}",
                // Move the CodeCov report to a different dir to not confuse Jenkins about results.xml
                "mkdir -v reports",
                "mv -v coverage.xml reports/coverage.xml",
                // Update the package wheel to PYPI
                "twine upload -u '${pypi_username}' -p '${pypi_password}' --repository-url https://upload.pypi.org/legacy/ --skip-existing dist/*"]

            // Add the build to the matrix
            matrix += bc
        }
    }

    // Submit the build configurations and execute them in parallel
    utils.run(matrix)
}
