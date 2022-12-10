with import <nixpkgs> {};
with pkgs.python310Packages;

let

  mutwo-timeline-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.timeline/archive/66534ff86647fd22ee2b23379a04cf0400617a0d.tar.gz";
  mutwo-timeline = import (mutwo-timeline-archive + "/default.nix");

  mutwo-abjad-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.abjad/archive/d7907a03ef9d1fed05c574456f1529b42bba84e8.tar.gz";
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
      rev = "9588b657f5e5fbd2aa4a7776262178e1a156dc5d";
      sha256 = "sha256-BDCLKsngU5MYA3NKBwcRQZ23ignjYnOIPgDkwNv5DQg=";
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
