class Peek < Formula
  include Language::Python::Virtualenv

  desc "htop for codebases — understand any repo in 5 seconds"
  homepage "https://github.com/hariomlohardev/peek"
  url "https://github.com/hariomlohardev/peek/archive/refs/tags/v0.6.0.tar.gz"
  sha256 "bd62f08423881f9503b292f669f8acaeb35a7477c1607a6d7b17a16817e9e4a3"
  license "MIT"

  depends_on "python@3.12"

  def install
    # pyproject.toml lives in the peek/ subdir (PyPI project root)
    cd "peek" do
      virtualenv_install_with_resources
    end
  end

  test do
    assert_match "peek", shell_output("#{bin}/peek --version")
  end
end
