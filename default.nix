{
  pkgs ? import <nixpkgs> {},
  pythonPackages ? pkgs.python37Packages,
  forTest ? true
}:
{
  cpytraceaflEnv = pkgs.stdenv.mkDerivation {
    name = "cpytraceafl-env";
    buildInputs = [
      pythonPackages.sysv_ipc
    ] ++ pkgs.stdenv.lib.optionals forTest [
      pythonPackages.pytest
      pythonPackages.pytestrunner
    ];
  };
}
