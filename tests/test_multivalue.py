import beets
import pytest
from beets.test.helper import PluginTestCase


class MultiValueModifyCliTest(PluginTestCase):
    plugin = "multivalue"

    ###
    # Real multi-value
    ###

    def test_list_add_value(self):
        self.enable_string_field()
        item = self.add_item(artists=["Eric"])
        self.run_command("multivalue", "-y", "artists+=Jamel")
        item.load()
        assert item.artists == ["Eric", "Jamel"]

    def test_list_remove_value(self):
        self.enable_string_field()
        item = self.add_item(artists=["Eric", "Jamel"])
        self.run_command("multivalue", "-y", "artists-=Jamel")
        item.load()
        assert item.artists == ["Eric"]

    def test_list_double_action(self):
        self.enable_string_field()
        item = self.add_item(artists=["Eric", "Jamel"])
        self.run_command("multivalue", "-y", "artists-=Jamel", "artists+=Jean")
        item.load()
        assert item.artists == ["Eric", "Jean"]

    def test_list_remove_no_match(self):
        self.enable_string_field()
        item = self.add_item(artists=["Eric"])
        self.run_command("multivalue", "-y", "artists-=Jamel")
        item.load()
        assert item.artists == ["Eric"]

    def test_list_remove_last(self):
        self.enable_string_field()
        item = self.add_item(artists=["Eric"])
        self.run_command("multivalue", "-y", "artists-=Eric")
        item.load()
        assert item.artists == []

    def test_list_add_first(self):
        self.enable_string_field()
        item = self.add_item(artists=[])
        self.run_command("multivalue", "-y", "artists+=Eric")
        item.load()
        assert item.artists == ["Eric"]

    ###
    # String multi-value
    ###

    def enable_string_field(self, sep=","):
        self.config["multivalue"]["string_fields"] = {"genre": sep}

    def test_string_add_value(self):
        self.enable_string_field()
        item = self.add_item(genre="Classic")
        self.run_command("multivalue", "-y", "genre+=Rock")
        item.load()
        assert item.genre == "Classic,Rock"

    def test_string_remove_value(self):
        self.enable_string_field()
        item = self.add_item(genre="Classic,Rock")
        self.run_command("multivalue", "-y", "genre-=Rock")
        item.load()
        assert item.genre == "Classic"

    def test_string_double_action(self):
        self.enable_string_field()
        item = self.add_item(genre="Classic,Rock")
        self.run_command("multivalue", "-y", "genre-=Rock", "genre+=Blues Chill")
        item.load()
        assert item.genre == "Classic,Blues Chill"

    def test_string_remove_no_match(self):
        self.enable_string_field()
        item = self.add_item(genre="Classic")
        self.run_command("multivalue", "-y", "genre-=Blues")
        item.load()
        assert item.genre == "Classic"

    def test_string_remove_last(self):
        self.enable_string_field()
        item = self.add_item(genre="Classic")
        self.run_command("multivalue", "-y", "genre-=Classic")
        item.load()
        assert item.genre == ""

    def test_string_add_first(self):
        self.enable_string_field()
        item = self.add_item(genre=None)
        self.run_command("multivalue", "-y", "genre+=Classic")
        item.load()
        assert item.genre == "Classic"

        item.genre = ""
        item.store()

        self.run_command("multivalue", "-y", "genre+=Classic")
        item.load()
        assert item.genre == "Classic"

    def test_string_other_sep(self):
        self.enable_string_field(";")
        item = self.add_item(genre="Classic")
        self.run_command("multivalue", "-y", "genre+=Blues")
        item.load()
        assert item.genre == "Classic;Blues"

    def test_string_unset(self):
        with pytest.raises(
            beets.ui.UserError, match=r"'genre' is not a declared multivalue field"
        ):
            self.run_command("multivalue", "-y", "genre+=Blues")

    ###
    # Compatibility with standard modify command
    ###

    def test_compatibility_with_modify_basic_field(self):
        """
        Test that multivalue command behaves the same as modify for basic
        field updates
        """
        # Test with a basic field that's not multivalue
        item = self.add_item(genre="Rock", grouping="Old Artist")

        # Use multivalue command to set a basic field (should work like modify)
        self.run_command("multivalue", "-y", "genre=Blues")
        item.load()
        assert item.genre == "Blues"
        assert item.grouping == "Old Artist"  # Should remain unchanged

        # Test with multiple basic fields
        self.run_command("multivalue", "-y", "grouping=New Artist", "year=2023")
        item.load()
        assert item.grouping == "New Artist"
        assert item.year == 2023

    def test_compatibility_with_modify_query_behavior(self):
        """Test that multivalue command uses the same query behavior as modify"""
        # Add multiple items
        item1 = self.add_item(artist="Artist A", title="Song 1")
        item2 = self.add_item(artist="Artist B", title="Song 2")
        item3 = self.add_item(artist="Artist A", title="Song 3")

        # Use multivalue command with query (should behave like modify)
        self.run_command("multivalue", "-y", "artist:Artist A", "genre=Rock")

        # Reload items
        item1.load()
        item2.load()
        item3.load()

        # Only items matching the query should be modified
        assert item1.genre == "Rock"
        assert item2.genre == ""  # Should remain unchanged
        assert item3.genre == "Rock"

    def test_compatibility_with_modify_field_deletion(self):
        """Test that multivalue command supports field deletion like modify"""
        item = self.add_item(grouping="Test Song", genre="Rock", year=2023)

        # Test field deletion with !
        self.run_command("multivalue", "-y", "genre!")
        item.load()
        assert item.genre == ""
        assert item.grouping == "Test Song"  # Should remain unchanged
        assert item.year == 2023  # Should remain unchanged

        # Test multiple field deletions
        self.run_command("multivalue", "-y", "grouping!", "year!")
        item.load()
        assert item.grouping == ""
        assert item.year == 0

    def test_compatibility_with_modify_mixed_operations(self):
        """Test that multivalue command supports mixed operations like modify"""
        self.enable_string_field()
        item = self.add_item(grouping="Old Artist", genre="Rock,Pop", year=2020)

        # Mix basic assignment, field deletion, and multivalue operations
        self.run_command(
            "multivalue", "-y", "grouping=New Artist", "year!", "genre+=Jazz"
        )
        item.load()
        assert item.grouping == "New Artist"
        assert item.year == 0
        assert item.genre == "Rock,Pop,Jazz"

    def test_compatibility_with_modify_command_options(self):
        """Test that multivalue command accepts the same options as modify command"""
        item = self.add_item(grouping="Test Song")

        # Test that multivalue command accepts common modify options
        # --write, --nowrite, --move, --nomove, --yes
        self.run_command(
            "multivalue", "-y", "--write", "--nomove", "grouping=New Title"
        )
        item.load()
        assert item.grouping == "New Title"

        # Test --nowrite option
        item.grouping = "Old Title"
        item.store()
        self.run_command("multivalue", "-y", "--nowrite", "grouping=New Title")
        item.load()
        assert item.grouping == "New Title"  # Should still update in database

    def test_compatibility_with_modify_no_matching_items(self):
        """Test that multivalue command has similar error handling to modify"""
        with pytest.raises(beets.ui.UserError, match=r"No matching items found\."):
            self.run_command("multivalue")

        with pytest.raises(beets.ui.UserError, match=r"No matching items found\."):
            self.run_command("multivalue", "-y", "nonexistent:query", "title=Test")
