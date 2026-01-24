"""Functional tests for wh WNS CLI commands (identity and alias management)."""

from unittest.mock import patch
from click.testing import CliRunner
import tempfile
from pathlib import Path
import json
import base64



class TestIdentityCreate:
    """Test wh identity create command."""

    def test_identity_create(self):
        """Test that 'wh identity create' generates a new key pair."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                result = runner.invoke(identity, ["create"])

                assert result.exit_code == 0
                assert "Created: wh://" in result.output
                assert ".wns" in result.output
                assert "Keys saved to:" in result.output
                assert "Share this address" in result.output

    def test_identity_create_with_name(self):
        """Test creating identity with --name flag."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                result = runner.invoke(identity, ["create", "--name", "my-server"])

                assert result.exit_code == 0
                assert "Created: wh://" in result.output
                assert "Name: my-server" in result.output


class TestIdentityList:
    """Test wh identity list command."""

    def test_identity_list(self):
        """Test that 'wh identity list' shows all identities."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create two test identities
                id1 = WNSIdentity.generate(name="server1")
                id2 = WNSIdentity.generate(name="server2")
                store.save_identity(id1)
                store.save_identity(id2)
                store.set_default_identity(id1.address)

                result = runner.invoke(identity, ["list"])

                assert result.exit_code == 0
                assert "ADDRESS" in result.output
                assert "NAME" in result.output
                assert id1.address in result.output
                assert id2.address in result.output
                assert "server1" in result.output
                assert "server2" in result.output
                assert "(default)" in result.output

    def test_identity_list_empty(self):
        """Test identity list with no identities."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                result = runner.invoke(identity, ["list"])

                assert result.exit_code == 0
                assert "No identities found" in result.output
                assert "Create one with: wh identity create" in result.output


class TestIdentityDefault:
    """Test wh identity default command."""

    def test_identity_default(self):
        """Test that 'wh identity default' shows current default."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create and set default
                test_id = WNSIdentity.generate(name="test-server")
                store.save_identity(test_id)
                store.set_default_identity(test_id.address)

                result = runner.invoke(identity, ["default"])

                assert result.exit_code == 0
                assert "Default identity: wh://" in result.output
                assert test_id.address in result.output
                assert "Name: test-server" in result.output


class TestIdentitySetDefault:
    """Test wh identity set-default command."""

    def test_identity_set_default(self):
        """Test that 'wh identity set-default NAME' changes default."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create identity
                test_id = WNSIdentity.generate(name="test-server")
                store.save_identity(test_id)

                result = runner.invoke(identity, ["set-default", test_id.address])

                assert result.exit_code == 0
                assert "Default set: wh://" in result.output
                assert test_id.address in result.output

                # Verify it was set
                assert store.get_default_identity_address() == test_id.address

    def test_identity_set_default_not_found(self):
        """Test set-default with non-existent identity."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                result = runner.invoke(identity, ["set-default", "nonexistent"])

                assert result.exit_code != 0
                assert "Identity not found" in result.output


class TestIdentityClearDefault:
    """Test wh identity clear-default command."""

    def test_identity_clear_default(self):
        """Test that 'wh identity clear-default' clears default."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create and set default
                test_id = WNSIdentity.generate()
                store.save_identity(test_id)
                store.set_default_identity(test_id.address)

                result = runner.invoke(identity, ["clear-default"])

                assert result.exit_code == 0
                assert "Default cleared" in result.output
                assert store.get_default_identity_address() is None


class TestIdentityShow:
    """Test wh identity show command."""

    def test_identity_show(self):
        """Test that 'wh identity show NAME' displays details."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create identity with scoped name
                test_id = WNSIdentity.generate(name="test-server")
                test_id.scoped_name = "laptop"
                store.save_identity(test_id)

                result = runner.invoke(identity, ["show", test_id.address])

                assert result.exit_code == 0
                assert f"Address: wh://{test_id.address}.wns" in result.output
                assert "Name: test-server" in result.output
                assert "Scoped name: laptop" in result.output
                assert "Public key:" in result.output
                assert "Has private key: yes" in result.output


class TestIdentityDelete:
    """Test wh identity delete command."""

    def test_identity_delete(self):
        """Test that 'wh identity delete NAME' removes identity."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create identity
                test_id = WNSIdentity.generate()
                store.save_identity(test_id)

                # Delete with --yes to skip prompt
                result = runner.invoke(identity, ["delete", test_id.address, "--yes"])

                assert result.exit_code == 0
                assert "Deleted" in result.output

                # Verify it was deleted
                assert store.load_identity(test_id.address) is None


class TestIdentityExport:
    """Test wh identity export command."""

    def test_identity_export(self):
        """Test that 'wh identity export NAME' outputs public key."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create identity
                test_id = WNSIdentity.generate(name="test-server")
                store.save_identity(test_id)

                result = runner.invoke(identity, ["export", test_id.address])

                assert result.exit_code == 0

                # Parse JSON output
                data = json.loads(result.output)
                assert data["address"] == test_id.address
                assert "public_key" in data
                assert data["name"] == "test-server"

    def test_identity_export_to_file(self):
        """Test exporting identity to file."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            output_file = Path(tmpdir) / "export.json"

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create identity
                test_id = WNSIdentity.generate()
                store.save_identity(test_id)

                result = runner.invoke(
                    identity, ["export", test_id.address, "-o", str(output_file)]
                )

                assert result.exit_code == 0
                assert "Exported to:" in result.output
                assert output_file.exists()


class TestIdentitySetName:
    """Test wh identity set-name command."""

    def test_identity_set_name(self):
        """Test that 'wh identity set-name ID NAME' updates local name."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                # Create identity
                test_id = WNSIdentity.generate()
                store.save_identity(test_id)

                result = runner.invoke(
                    identity, ["set-name", test_id.address, "my-laptop"]
                )

                assert result.exit_code == 0
                assert "Scoped name set:" in result.output
                assert "my-laptop" in result.output

                # Verify it was set
                loaded = store.load_identity(test_id.address)
                assert loaded.scoped_name == "my-laptop"


class TestIdentityClaimName:
    """Test wh identity claim-name command."""

    def test_identity_claim_name(self):
        """Test that 'wh identity claim-name NAME' registers WNS name."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity
        from wh.wns.names import NameClaimStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.WNSIdentityStore") as mock_id_store, \
                 patch("wh.wns.cli.NameClaimStore") as mock_name_store:

                id_store = WNSIdentityStore(base_path=base_path)
                name_store = NameClaimStore(base_path=base_path)
                mock_id_store.return_value = id_store
                mock_name_store.return_value = name_store

                # Create identity
                test_id = WNSIdentity.generate()
                id_store.save_identity(test_id)

                result = runner.invoke(identity, ["claim-name", "my-laptop"])

                assert result.exit_code == 0
                assert "Claimed: wh://my-laptop.wns" in result.output
                assert test_id.address in result.output

                # Verify claim was saved
                claim = name_store.load_claim("my-laptop")
                assert claim is not None
                assert claim.name == "my-laptop"
                assert claim.address == test_id.address


class TestIdentityListNames:
    """Test wh identity list-names command."""

    def test_identity_list_names(self):
        """Test that 'wh identity list-names' shows claimed names."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentity
        from wh.wns.names import NameClaimStore, NameClaim

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.NameClaimStore") as mock_name_store:
                name_store = NameClaimStore(base_path=base_path)
                mock_name_store.return_value = name_store

                # Create test identity and claim
                test_id = WNSIdentity.generate()
                claim = NameClaim.create(test_id, "my-laptop")
                name_store.save_claim(claim)

                result = runner.invoke(identity, ["list-names"])

                assert result.exit_code == 0
                assert "NAME" in result.output
                assert "ADDRESS" in result.output
                assert "STATUS" in result.output
                assert "my-laptop" in result.output
                assert test_id.address in result.output

    def test_identity_list_names_empty(self):
        """Test list-names with no claims."""
        from wh.wns.cli import identity
        from wh.wns.names import NameClaimStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.NameClaimStore") as mock_name_store:
                name_store = NameClaimStore(base_path=base_path)
                mock_name_store.return_value = name_store

                result = runner.invoke(identity, ["list-names"])

                assert result.exit_code == 0
                assert "No names claimed" in result.output


class TestIdentityReleaseName:
    """Test wh identity release-name command."""

    def test_identity_release_name(self):
        """Test that 'wh identity release-name NAME' releases WNS name."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentity
        from wh.wns.names import NameClaimStore, NameClaim

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.NameClaimStore") as mock_name_store:
                name_store = NameClaimStore(base_path=base_path)
                mock_name_store.return_value = name_store

                # Create claim
                test_id = WNSIdentity.generate()
                claim = NameClaim.create(test_id, "my-laptop")
                name_store.save_claim(claim)

                result = runner.invoke(
                    identity, ["release-name", "my-laptop", "--yes"]
                )

                assert result.exit_code == 0
                assert "Released: my-laptop" in result.output

                # Verify claim was deleted
                assert name_store.load_claim("my-laptop") is None


class TestIdentityImport:
    """Test wh identity import command."""

    def test_identity_import(self):
        """Test that 'wh identity import FILE' imports from file."""
        from wh.wns.cli import identity
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            import_file = Path(tmpdir) / "import.json"

            # Create export file
            test_id = WNSIdentity.generate(name="imported-server")
            export_data = {
                "address": test_id.address,
                "full_address": test_id.full_address,
                "public_key": base64.b64encode(test_id.public_key).decode("ascii"),
                "name": "imported-server",
            }
            import_file.write_text(json.dumps(export_data))

            with patch("wh.wns.cli.WNSIdentityStore") as mock_store_class:
                store = WNSIdentityStore(base_path=base_path)
                mock_store_class.return_value = store

                result = runner.invoke(identity, ["import", str(import_file)])

                assert result.exit_code == 0
                assert "Added to known hosts:" in result.output
                assert test_id.address in result.output


class TestAliasAdd:
    """Test wh alias add command."""

    def test_alias_add(self):
        """Test that 'wh alias add NAME TARGET' stores alias."""
        from wh.wns.cli import alias
        from wh.wns.aliases import AliasStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.AliasStore") as mock_store_class:
                store = AliasStore(base_path=base_path)
                mock_store_class.return_value = store

                result = runner.invoke(
                    alias, ["add", "laptop", "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns"]
                )

                assert result.exit_code == 0
                assert "Added: laptop" in result.output

                # Verify alias was added
                saved = store.get("laptop")
                assert saved is not None
                assert saved.address == "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns"

    def test_alias_add_with_description(self):
        """Test adding alias with description and username."""
        from wh.wns.cli import alias
        from wh.wns.aliases import AliasStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.AliasStore") as mock_store_class:
                store = AliasStore(base_path=base_path)
                mock_store_class.return_value = store

                result = runner.invoke(
                    alias,
                    [
                        "add", "server",
                        "wh://6wcqynbx6sqc4swwtojhr62jcm.wns",
                        "-d", "Production server",
                        "-u", "admin"
                    ]
                )

                assert result.exit_code == 0
                assert "Description: Production server" in result.output
                assert "Default username: admin" in result.output


class TestAliasRemove:
    """Test wh alias remove command."""

    def test_alias_remove(self):
        """Test that 'wh alias remove NAME' deletes alias."""
        from wh.wns.cli import alias
        from wh.wns.aliases import AliasStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.AliasStore") as mock_store_class:
                store = AliasStore(base_path=base_path)
                mock_store_class.return_value = store

                # Add alias first
                store.add("laptop", "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns")

                result = runner.invoke(alias, ["remove", "laptop"])

                assert result.exit_code == 0
                assert "Removed: laptop" in result.output

                # Verify alias was removed
                assert store.get("laptop") is None


class TestAliasList:
    """Test wh alias list command."""

    def test_alias_list(self):
        """Test that 'wh alias list' shows all aliases."""
        from wh.wns.cli import alias
        from wh.wns.aliases import AliasStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.AliasStore") as mock_store_class:
                store = AliasStore(base_path=base_path)
                mock_store_class.return_value = store

                # Add test aliases
                store.add("laptop", "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns", description="My laptop")
                store.add("server", "wh://6wcqynbx6sqc4swwtojhr62jcm.wns", description="Work server", username="admin")

                result = runner.invoke(alias, ["list"])

                assert result.exit_code == 0
                assert "NAME" in result.output
                assert "ADDRESS" in result.output
                assert "DESCRIPTION" in result.output
                assert "laptop" in result.output
                assert "server" in result.output
                assert "My laptop" in result.output


class TestAliasShow:
    """Test wh alias show command."""

    def test_alias_show(self):
        """Test that 'wh alias show NAME' shows single alias."""
        from wh.wns.cli import alias
        from wh.wns.aliases import AliasStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.AliasStore") as mock_store_class:
                store = AliasStore(base_path=base_path)
                mock_store_class.return_value = store

                # Add test alias
                store.add(
                    "laptop",
                    "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns",
                    description="My laptop",
                    username="user"
                )

                result = runner.invoke(alias, ["show", "laptop"])

                assert result.exit_code == 0
                assert "Name: laptop" in result.output
                assert "Address: wh://bvu3qtwzmi7wy27rypx6qiyqti.wns" in result.output
                assert "Description: My laptop" in result.output
                assert "Default username: user" in result.output


class TestAliasResolve:
    """Test wh alias resolve command."""

    def test_alias_resolve(self):
        """Test that 'wh alias resolve NAME' resolves target."""
        from wh.wns.cli import alias
        from wh.wns.aliases import AliasStore

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            with patch("wh.wns.cli.AliasStore") as mock_store_class:
                store = AliasStore(base_path=base_path)
                mock_store_class.return_value = store

                # Add test alias
                store.add("laptop", "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns")

                result = runner.invoke(alias, ["resolve", "laptop"])

                assert result.exit_code == 0
                assert result.output.strip() == "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns"


class TestWNSIntegration:
    """Integration tests for WNS functionality."""

    def test_wns_url_resolution(self):
        """Test that wh:// URL resolution returns correct code."""
        from wh.wns.identity import WNSIdentity, parse_wns_address

        # Generate identity and verify address parsing
        test_id = WNSIdentity.generate()

        # Test various formats
        formats = [
            f"wh://{test_id.address}.wns",
            f"{test_id.address}.wns",
            test_id.address,
            f"user@wh://{test_id.address}.wns"
        ]

        for fmt in formats:
            parsed = parse_wns_address(fmt)
            assert parsed == test_id.address

    def test_alias_resolve_fallback_wns(self):
        """Test that local alias miss falls back to WNS lookup."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            store = AliasStore(base_path=base_path)

            # Test that WNS addresses pass through even if not an alias
            wns_addr = "wh://bvu3qtwzmi7wy27rypx6qiyqti.wns"
            resolved = store.resolve(wns_addr)
            assert resolved == wns_addr

            # Test that non-alias, non-WNS returns None
            resolved = store.resolve("nonexistent")
            assert resolved is None

    def test_identity_create_with_name_integration(self):
        """Integration test: Create with --name flag and verify storage."""
        from wh.wns.identity import WNSIdentityStore, WNSIdentity

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            store = WNSIdentityStore(base_path=base_path)

            # Create identity with name
            test_id = WNSIdentity.generate(name="integration-test")
            store.save_identity(test_id)

            # Load it back
            loaded = store.load_identity(test_id.address)
            assert loaded is not None
            assert loaded.name == "integration-test"
            assert loaded.address == test_id.address

            # Set as default
            store.set_default_identity(test_id.address)
            default = store.get_default_identity()
            assert default.address == test_id.address

            # List identities
            all_ids = store.list_identities()
            assert len(all_ids) == 1
            assert all_ids[0].name == "integration-test"
