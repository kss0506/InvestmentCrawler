{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.chromedriver
    pkgs.chromium
    pkgs.geckodriver
    pkgs.postgresql
    pkgs.openssl
  ];
}
