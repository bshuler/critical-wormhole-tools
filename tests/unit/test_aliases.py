"""Unit tests for WNS aliases module."""

import tempfile
from pathlib import Path


class TestAlias:
    """Tests for Alias dataclass."""

    def test_create_alias(self):
        """Test creating an alias."""
        from wh.wns.aliases import Alias

        alias = Alias(
            name="laptop",
            address="wh://abcdefghijklmnopqrstuvwxyz.wns",
        )

        assert alias.name == "laptop"
        assert alias.address == "wh://abcdefghijklmnopqrstuvwxyz.wns"
        assert alias.username is None
        assert alias.description is None

    def test_create_alias_with_optional_fields(self):
        """Test creating alias with all fields."""
        from wh.wns.aliases import Alias

        alias = Alias(
            name="work-server",
            address="wh://abcdefghijklmnopqrstuvwxy2.wns",
            username="admin",
            description="Work development server",
        )

        assert alias.name == "work-server"
        assert alias.address == "wh://abcdefghijklmnopqrstuvwxy2.wns"
        assert alias.username == "admin"
        assert alias.description == "Work development server"

    def test_to_dict(self):
        """Test converting alias to dict."""
        from wh.wns.aliases import Alias

        alias = Alias(
            name="laptop",
            address="wh://abcdefghijklmnopqrstuvwxyz.wns",
            username="user",
        )

        d = alias.to_dict()

        assert d["name"] == "laptop"
        assert d["address"] == "wh://abcdefghijklmnopqrstuvwxyz.wns"
        assert d["username"] == "user"
        # None values should be omitted
        assert "description" not in d

    def test_from_dict(self):
        """Test creating alias from dict."""
        from wh.wns.aliases import Alias

        data = {
            "name": "server",
            "address": "wh://abcdefghijklmnopqrstuvwxy3.wns",
            "username": "root",
            "description": "Main server",
        }

        alias = Alias.from_dict(data)

        assert alias.name == "server"
        assert alias.address == "wh://abcdefghijklmnopqrstuvwxy3.wns"
        assert alias.username == "root"
        assert alias.description == "Main server"


class TestAliasStore:
    """Tests for AliasStore class."""

    def test_init_default(self):
        """Test AliasStore with default path."""
        from wh.wns.aliases import AliasStore

        store = AliasStore()
        expected = Path.home() / ".wh"
        assert store.base_path == expected

    def test_init_custom_path(self):
        """Test AliasStore with custom path."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))
            assert store.base_path == Path(tmpdir)

    def test_add_and_get_alias(self):
        """Test adding and retrieving an alias."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            store.add("test", "wh://abcdefghijklmnopqrstuvwxyz.wns")

            retrieved = store.get("test")
            assert retrieved is not None
            assert retrieved.name == "test"
            assert retrieved.address == "wh://abcdefghijklmnopqrstuvwxyz.wns"

    def test_get_nonexistent(self):
        """Test getting nonexistent alias returns None."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            result = store.get("nonexistent")
            assert result is None

    def test_remove_alias(self):
        """Test removing an alias."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            store.add("test", "wh://abcdefghijklmnopqrstuvwxyz.wns")
            assert store.get("test") is not None

            result = store.remove("test")
            assert result is True
            assert store.get("test") is None

    def test_remove_nonexistent(self):
        """Test removing nonexistent alias returns False."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            result = store.remove("nonexistent")
            assert result is False

    def test_list_aliases(self):
        """Test listing all aliases."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            store.add("a", "wh://abcdefghijklmnopqrstuvwxy7.wns")
            store.add("b", "wh://bcdefghijklmnopqrstuvwxyz2.wns")
            store.add("c", "wh://cdefghijklmnopqrstuvwxyz23.wns")

            aliases = store.list()
            assert len(aliases) == 3
            names = [a.name for a in aliases]
            assert "a" in names
            assert "b" in names
            assert "c" in names

    def test_list_empty(self):
        """Test listing empty store."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            aliases = store.list()
            assert aliases == []

    def test_persistence(self):
        """Test aliases persist across store instances."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and add alias
            store1 = AliasStore(base_path=Path(tmpdir))
            store1.add("persistent", "wh://abcdefghijklmnopqrstuvwxyz.wns")

            # Create new store instance
            store2 = AliasStore(base_path=Path(tmpdir))
            retrieved = store2.get("persistent")

            assert retrieved is not None
            assert retrieved.address == "wh://abcdefghijklmnopqrstuvwxyz.wns"

    def test_update_alias(self):
        """Test updating an existing alias."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            # Add initial alias
            store.add("test", "wh://abcdefghijklmnopqrstuvwxy5.wns")

            # Update with new address (requires overwrite=True)
            store.add("test", "wh://abcdefghijklmnopqrstuvwxy6.wns", overwrite=True)

            retrieved = store.get("test")
            assert retrieved.address == "wh://abcdefghijklmnopqrstuvwxy6.wns"

    def test_resolve_alias(self):
        """Test resolving an alias to address."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            store.add("laptop", "wh://defghijklmnopqrstuvwxyz234.wns")

            address = store.resolve("laptop")
            assert address == "wh://defghijklmnopqrstuvwxyz234.wns"

    def test_resolve_nonexistent(self):
        """Test resolving nonexistent alias returns None."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            address = store.resolve("nonexistent")
            assert address is None

    def test_add_with_description(self):
        """Test adding alias with description."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            store.add("server", "wh://abcdefghijklmnopqrstuvwxy4.wns", description="Main server")

            alias = store.get("server")
            assert alias.description == "Main server"

    def test_add_with_username(self):
        """Test adding alias with default username."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            store.add("server", "wh://abcdefghijklmnopqrstuvwxy4.wns", username="admin")

            alias = store.get("server")
            assert alias.username == "admin"

    def test_add_duplicate_raises(self):
        """Test adding duplicate alias without overwrite raises."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            store.add("dup", "wh://abcdefghijklmnopqrstuvwxy4.wns")

            # Adding again without overwrite should raise
            try:
                store.add("dup", "wh://abcdefghijklmnopqrstuvwxy5.wns")
                assert False, "Should have raised"
            except ValueError:
                pass  # Expected


class TestAliasStoreEdgeCases:
    """Edge case tests for AliasStore."""

    def test_aliases_file_path(self):
        """Test aliases file is created in correct location."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))
            store.add("test", "wh://abcdefghijklmnopqrstuvwxyz.wns")

            aliases_file = Path(tmpdir) / "aliases.json"
            assert aliases_file.exists()

    def test_invalid_json_handling(self):
        """Test handling of invalid JSON in aliases file."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid JSON file
            aliases_file = Path(tmpdir) / "aliases.json"
            aliases_file.write_text("not valid json{{{")

            store = AliasStore(base_path=Path(tmpdir))

            # Should handle gracefully
            aliases = store.list()
            assert aliases == []

    def test_empty_name_handling(self):
        """Test handling of empty alias name."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            # Getting empty name returns None
            result = store.get("")
            assert result is None


class TestAliasToDict:
    """Tests for Alias to_dict method."""

    def test_to_dict_minimal(self):
        """Test to_dict with only required fields."""
        from wh.wns.aliases import Alias

        alias = Alias(
            name="minimal",
            address="wh://abcdefghijklmnopqrstuvwxyz.wns",
        )

        d = alias.to_dict()

        assert "name" in d
        assert "address" in d
        assert "username" not in d
        assert "description" not in d

    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        from wh.wns.aliases import Alias

        alias = Alias(
            name="full",
            address="wh://abcdefghijklmnopqrstuvwxyz.wns",
            username="user",
            description="Full alias",
        )

        d = alias.to_dict()

        assert len(d) == 4
        assert d["username"] == "user"
        assert d["description"] == "Full alias"


class TestAliasStoreFileOperations:
    """Tests for AliasStore file operations."""

    def test_save_and_load(self):
        """Test saving and loading aliases."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = AliasStore(base_path=Path(tmpdir))

            # Add multiple aliases (use valid 26-char addresses)
            store.add("a1", "wh://abcdefghijklmnopqrstuvwxyz.wns")
            store.add("a2", "wh://bcdefghijklmnopqrstuvwxyza.wns")

            # Reload from disk
            store2 = AliasStore(base_path=Path(tmpdir))
            aliases = store2.list()

            assert len(aliases) == 2

    def test_base_path_property(self):
        """Test base_path property."""
        from wh.wns.aliases import AliasStore

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            store = AliasStore(base_path=path)

            assert store.base_path == path
