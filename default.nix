with import <nixpkgs> {};
with pkgs.python310Packages;

let

  mutwo-core-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.core/archive/61ebb657ef5806eb067f5df6885254fdbae8f44c.tar.gz";
  mutwo-core = import (mutwo-core-archive + "/default.nix");

  mutwo-timeline-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.timeline/archive/5a6e1d7b72ea584f00e091aeceb2a029cd8f5802.tar.gz";
  mutwo-timeline = import (mutwo-timeline-archive + "/default.nix");

  mutwo-abjad-archive = builtins.fetchTarball "https://github.com/mutwo-org/mutwo.abjad/archive/1d9114da453c040640d568fc260149ed4eccfe70.tar.gz";
  mutwo-abjad = import (mutwo-abjad-archive + "/default.nix");

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
    ];
    checkPhase = ''
      runHook preCheck
      pytest
      runHook postCheck
    '';
    doCheck = true;
  }
