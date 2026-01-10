# Homebrew formula for Critical Wormhole Tools
# Install: brew install bshuler/tap/critical-wormhole-tools
# Or: brew tap bshuler/tap && brew install critical-wormhole-tools

class CriticalWormholeTools < Formula
  include Language::Python::Virtualenv

  desc "Secure network utilities using Magic Wormhole code-based addressing"
  homepage "https://github.com/bshuler/critical-wormhole-tools"
  url "https://files.pythonhosted.org/packages/source/c/critical_wormhole_tools/critical_wormhole_tools-0.4.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"
  head "https://github.com/bshuler/critical-wormhole-tools.git", branch: "main"

  depends_on "python@3.12"
  depends_on "libsodium"
  depends_on "openssl@3"

  resource "magic-wormhole" do
    url "https://files.pythonhosted.org/packages/source/m/magic-wormhole/magic_wormhole-0.14.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "asyncssh" do
    url "https://files.pythonhosted.org/packages/source/a/asyncssh/asyncssh-2.14.2.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.7.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "twisted" do
    url "https://files.pythonhosted.org/packages/source/t/twisted/twisted-24.3.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "attrs" do
    url "https://files.pythonhosted.org/packages/source/a/attrs/attrs-23.2.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/source/h/httpx/httpx-0.27.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.1.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "noiseprotocol" do
    url "https://files.pythonhosted.org/packages/source/n/noiseprotocol/noiseprotocol-0.3.1.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pynacl" do
    url "https://files.pythonhosted.org/packages/source/p/pynacl/PyNaCl-1.5.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "aiohttp" do
    url "https://files.pythonhosted.org/packages/source/a/aiohttp/aiohttp-3.9.5.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/p/pyyaml/PyYAML-6.0.1.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources

    # Generate shell completions
    generate_completions_from_executable(bin/"wh", shells: [:bash, :zsh, :fish], shell_parameter_format: :click)
  end

  test do
    assert_match "Critical Wormhole Tools", shell_output("#{bin}/wh --version")
    assert_match "nc", shell_output("#{bin}/wh --help")
  end
end
