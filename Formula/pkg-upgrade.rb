class PkgUpgrade < Formula
  include Language::Python::Virtualenv

  desc "Beautiful TUI dashboard to upgrade all macOS package managers"
  homepage "https://github.com/liskeee/pkg-upgrade"
  url "https://github.com/liskeee/pkg-upgrade/archive/refs/tags/v0.1.0.tar.gz"
  # Replace with the sha256 of the tagged release tarball:
  #   curl -L <url> | shasum -a 256
  sha256 "REPLACE_WITH_RELEASE_TARBALL_SHA256"
  license "MIT"

  depends_on "python@3.12"

  # `brew update-python-resources Formula/pkg-upgrade.rb` regenerates these.
  resource "textual" do
    url "https://files.pythonhosted.org/packages/source/t/textual/textual-3.0.0.tar.gz"
    sha256 "REPLACE_WITH_TEXTUAL_SDIST_SHA256"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.9.4.tar.gz"
    sha256 "REPLACE_WITH_RICH_SDIST_SHA256"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/source/m/markdown-it-py/markdown-it-py-3.0.0.tar.gz"
    sha256 "REPLACE_WITH_MDIT_SDIST_SHA256"
  end

  resource "mdurl" do
    url "https://files.pythonhosted.org/packages/source/m/mdurl/mdurl-0.1.2.tar.gz"
    sha256 "REPLACE_WITH_MDURL_SDIST_SHA256"
  end

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/source/P/Pygments/pygments-2.18.0.tar.gz"
    sha256 "REPLACE_WITH_PYGMENTS_SDIST_SHA256"
  end

  resource "linkify-it-py" do
    url "https://files.pythonhosted.org/packages/source/l/linkify-it-py/linkify-it-py-2.0.3.tar.gz"
    sha256 "REPLACE_WITH_LINKIFY_SDIST_SHA256"
  end

  resource "uc-micro-py" do
    url "https://files.pythonhosted.org/packages/source/u/uc-micro-py/uc-micro-py-1.0.3.tar.gz"
    sha256 "REPLACE_WITH_UCMICRO_SDIST_SHA256"
  end

  resource "platformdirs" do
    url "https://files.pythonhosted.org/packages/source/p/platformdirs/platformdirs-4.3.6.tar.gz"
    sha256 "REPLACE_WITH_PLATFORMDIRS_SDIST_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "pkg-upgrade", shell_output("#{bin}/pkg-upgrade --version")
  end
end
