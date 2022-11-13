with import <nixpkgs> {};
with pkgs.python310Packages;

let

  mutwo-core-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.core/archive/83efe12fb98119e03db833c231f9c87956577b3f.tar.gz";
  mutwo-core = import (mutwo-core-archive + "/default.nix");

  mutwo-timeline-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.timeline/archive/295b9b6ef5ec5099fc940962513b5f30d284f9a0.tar.gz";
  mutwo-timeline = import (mutwo-timeline-archive + "/default.nix");

  mutwo-abjad-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.abjad/archive/0cd25e7e87ae61ebfb0343a59baf8b8564c24fca.tar.gz";
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
      rev = "d8ec262438546cef6063ee797cc074a630c9bc4c";
      sha256 = "sha256-YDGad5sDUKNt4UOf6jO/JwwyenDSgBYQA+H0Dt9b08A=";
    };
    checkInputs = [
      python310Packages.pytest
      lilypond-with-fonts
    ];
    propagatedBuildInputs = [ 
      mutwo-core
      mutwo-timeline
      mutwo-abjad
      lilypond-with-fonts
      treelib
    ];
    checkPhase = ''
      runHook preCheck
      pytest
      runHook postCheck
    '';
    doCheck = true;
  }
