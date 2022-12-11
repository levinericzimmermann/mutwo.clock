with import <nixpkgs> {};
with pkgs.python310Packages;

let

  mutwo-timeline-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.timeline/archive/66534ff86647fd22ee2b23379a04cf0400617a0d.tar.gz";
  mutwo-timeline = import (mutwo-timeline-archive + "/default.nix");

  mutwo-abjad-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.abjad/archive/2314faaa2babf0e1b98f46a30dc9886609e6f3be.tar.gz";
  mutwo-abjad = import (mutwo-abjad-archive + "/default.nix");

  treelib = pkgs.python310Packages.buildPythonPackage rec {
    name = "treelib";
    src = fetchFromGitHub {
      owner = "caesar0301";
      repo = name;
      rev = "12d7efd50829a5a18edaab01911b1e546bff2ede";
      sha256 = "sha256-QGgWsMfPm4ZCSeU/ODY0ewg1mu/mRmtXgHtDyHT9dac=";
    };
    doCheck = true;
    propagatedBuildInputs = [ python310Packages.future ];
  };

in

  buildPythonPackage rec {
    name = "mutwo.clock";
    src = fetchFromGitHub {
      owner = "levinericzimmermann";
      repo = name;
      rev = "d0b6fe95fe44a1f551a97b1451341e8911ee3652";
      sha256 = "sha256-pe0Xq7qmyAJnrPkCg5m04yYgg8WtMcvPzlRgdHZ6YK0=";
    };
    checkInputs = [
      python310Packages.pytest
      lilypond-with-fonts
    ];
    propagatedBuildInputs = [ 
      mutwo-timeline
      mutwo-abjad
      lilypond-with-fonts
      treelib
      python310Packages.numpy
    ];
    checkPhase = ''
      runHook preCheck
      pytest
      runHook postCheck
    '';
    doCheck = true;
  }
