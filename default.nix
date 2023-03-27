{ sources ? import ./nix/sources.nix}:
let
  mutwo-clock = import (sources.mutwo-nix.outPath + "/mutwo.clock/default.nix") {};
  mutwo-clock-local = mutwo-clock.overrideAttrs (
    finalAttrs: previousAttrs: {
       src = ./.;
    }
  );
in
  mutwo-clock-local
