class Peek < Formula
  include Language::Python::Virtualenv

  desc "htop for codebases — understand any repo in 5 seconds"
  homepage "https://github.com/hariomlohardev/peek"
  url "https://github.com/hariomlohardev/peek/archive/refs/tags/v0.5.0.tar.gz"
  sha256 "6f3854c79ce0819c032918ba3ea7f011d2e9a2e96d65d0a822e809c1a0d433b0"
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
