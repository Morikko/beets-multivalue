import beets
import pytest
from beets.test.helper import PluginTestCase
from parameterized import parameterized


class MultiValueModifyCliTest(PluginTestCase):
    plugin = "multivalue"

    def enable_string_field(self, sep=","):
        self.config["multivalue"]["string_fields"] = {"genre": sep}

    ##
    # Multi-value cases
    ##

    @parameterized.expand(
        [
            # list_add_value
            ("list", "artists", ["Eric"], "artists+=Jamel", ["Eric", "Jamel"]),
            # list_remove_value
            ("list", "artists", ["Eric", "Jamel"], "artists-=Jamel", ["Eric"]),
            ("list", "artists", ["Jamel", "Eric", "Jamel"], "artists-=Jamel", ["Eric"]),
            # list_double_action
            (
                "list",
                "artists",
                ["Eric", "Jamel"],
                "artists-=Jamel artists+=Jean",
                ["Eric", "Jean"],
            ),
            # list_add_existing default is exact match
            ("list", "artists", ["Eric"], "artists+=Eric", ["Eric"]),
            ("list", "artists", ["eric"], "artists+=Eric", ["eric", "Eric"]),
            # list_remove_no_match
            ("list", "artists", ["Eric"], "artists-=Jamel", ["Eric"]),
            # list_remove_last
            ("list", "artists", ["Eric"], "artists-=Eric", []),
            # list_add_first
            ("list", "artists", [], "artists+=Eric", ["Eric"]),
            # list_add_match_insensitive
            ("list", "artists", ["Eric"], "artists+=~Eric", ["Eric"]),
            ("list", "artists", ["eric"], "artists+=~Eric", ["eric"]),
            # list_remove_match_insensitive
            ("list", "artists", ["Eric"], "artists-=~Eric", []),
            ("list", "artists", ["eric"], "artists-=~Eric", []),
            # list_remove_match_regex
            ("list", "artists", ["Eric & Max"], "artists-=:Eric.*", []),
            # list_clean_regex_add
            (
                "list",
                "artists",
                ["Eric & Max"],
                "artists-=:Eric.* artists+=Eric",
                ["Eric"],
            ),
            # list_test_order
            (
                "list",
                "artists",
                ["original"],
                r"artists+=base artists-=base artists=base\␀pivot",
                ["pivot", "base"],
            ),
            # list_reset
            (
                "list",
                "artists",
                ["original"],
                "artists+=new artists= artists+=new2",
                ["new", "new2"],
            ),
            # list_del_win
            (
                "list",
                "artists",
                ["original"],
                r"artists! artists+=base artists-=base artists=base\␀pivot",
                [],
            ),
            # string_add_value
            ("string", "genre", "Classic", "genre+=Rock", "Classic,Rock"),
            # string_remove_value
            ("string", "genre", "Classic,Rock", "genre-=Rock", "Classic"),
            ("string", "genre", "Rock,Classic,Rock", "genre-=Rock", "Classic"),
            # string_double_action
            (
                "string",
                "genre",
                "Classic,Rock",
                "genre-=Rock genre+=Blues-Chill",
                "Classic,Blues-Chill",
            ),
            # string_add_existing default is exact match
            ("string", "genre", "Classic", "genre+=Classic", "Classic"),
            ("string", "genre", "classic", "genre+=Classic", "classic,Classic"),
            # string_remove_no_match
            ("string", "genre", "Classic", "genre-=Blues", "Classic"),
            # string_remove_last
            ("string", "genre", "Classic", "genre-=Classic", ""),
            # string_add_first_none
            ("string", "genre", None, "genre+=Classic", "Classic"),
            # string_add_first_empty
            ("string", "genre", "", "genre+=Classic", "Classic"),
            # string_add_match_insensitive
            ("string", "genre", "Classic", "genre+=~Classic", "Classic"),
            ("string", "genre", "classic", "genre+=~Classic", "classic"),
            # string_remove_match_insensitive
            ("string", "genre", "Classic", "genre-=~Classic", ""),
            ("string", "genre", "classic", "genre-=~Classic", ""),
            # string_remove_match_regex
            ("string", "genre", "Rock&Roll", "genre-=:Rock.*", ""),
            # string_clean_regex_add
            ("string", "genre", "Rock&Roll", "genre-=:Rock.* genre+=Rock", "Rock"),
            # string_test_order
            (
                "string",
                "genre",
                "original",
                "genre+=base genre-=base genre=base,pivot",
                "pivot,base",
            ),
            # string_reset
            (
                "string",
                "genre",
                "original",
                "genre+=new genre= genre+=new2",
                "new,new2",
            ),
            # string_del_win
            (
                "string",
                "genre",
                "original",
                "genre! genre+=base genre-=base genre=base,pivot",
                "",
            ),
        ]
    )
    def test_multimodify_operations(
        self, field_type, field_name, initial_value, command, expected_value
    ):
        """Test various multimodify operations for both list and string fields"""
        if field_type == "string":
            self.enable_string_field()

        # Handle None initial value for string fields
        if field_type == "string" and initial_value is None:
            item = self.add_item(**{field_name: None})
        else:
            item = self.add_item(**{field_name: initial_value})

        # Split command if it contains multiple operations
        commands = command.split()
        self.run_command("multimodify", "-y", *commands)
        item.load()

        assert getattr(item, field_name) == expected_value

    def test_multimodify_unsupported_add_regex_match(self):
        with pytest.raises(
            beets.ui.UserError, match=r"Regex is not supported when adding a value"
        ):
            self.run_command("multimodify", "-y", "artists+=:Rock.*")

    @parameterized.expand(
        [
            ("list", "artists", ["Éric"], "artists+=#Èric", ["Éric"]),
            ("list", "artists", [], "artists+=#Èric", ["Èric"]),
            ("list", "artists", ["Éric"], "artists-=#Èric", []),
            ("string", "genre", "Éric", "genre+=#Èric", "Éric"),
            ("string", "genre", "", "genre+=#Èric", "Èric"),
            ("string", "genre", "Éric", "genre-=#Èric", ""),
        ]
    )
    def test_multivalue_operations_plugin(
        self, field_type, field_name, initial_value, command, expected_value
    ):
        """
        Check a query mode added by a plugin is supported.
        """
        # Hack: PluginTestCase only supports enabling a single plugin. This test
        # needs a second one. Re-Execute the PluginMixin.load_plugins but
        # without updating the original values. At the end of this test, the
        # original unload_plugins() would be called to clean everything. No need
        # to do it here.
        #
        # Clear cache to reload plugins
        beets.plugins._instances.clear()
        required_plugins = ("multivalue", "bareasc")
        beets.config["plugins"] = required_plugins
        beets.plugins.load_plugins(required_plugins)
        beets.plugins.find_plugins()

        if field_type == "string":
            self.enable_string_field()

        # Handle None initial value for string fields
        if field_type == "string" and initial_value is None:
            item = self.add_item(**{field_name: None})
        else:
            item = self.add_item(**{field_name: initial_value})

        # Split command if it contains multiple operations
        commands = command.split()
        self.run_command("multimodify", "-y", *commands)
        item.load()

        assert getattr(item, field_name) == expected_value

    @parameterized.expand(
        [
            # comma_separator
            (",", "Classic", "genre+=Rock", "Classic,Rock"),
            # semicolon_separator
            (";", "Classic", "genre+=Blues", "Classic;Blues"),
            # pipe_separator
            ("|", "Rock", "genre+=Pop", "Rock|Pop"),
        ]
    )
    def test_string_separators(self, separator, initial_value, command, expected_value):
        """Test different string field separators"""
        self.enable_string_field(separator)
        item = self.add_item(genre=initial_value)
        self.run_command("multimodify", "-y", command)
        item.load()
        assert item.genre == expected_value

    def test_string_unset(self):
        with pytest.raises(
            beets.ui.UserError, match=r"'genre' is not a declared multivalue field"
        ):
            self.run_command("multimodify", "-y", "genre+=Blues")

    @parameterized.expand(
        [
            ("mmod",),
            ("mm",),
        ]
    )
    def test_multimodify_alias(self, alias):
        item = self.add_item(artists=[])
        self.run_command(alias, "-y", "artists+=Eric")
        item.load()
        assert item.artists == ["Eric"]

    ###
    # Compatibility with standard modify command
    ###

    @parameterized.expand(
        [
            # basic_field_assignment
            (
                {"genre": "Rock", "grouping": "Old Artist"},
                ["genre=Blues"],
                {"genre": "Blues"},
                {"grouping": "Old Artist"},
            ),
            # multiple_field_assignments
            (
                {"grouping": "Old Title", "genre": "Rock", "year": 2020},
                ["grouping=New Title", "year=2023"],
                {"grouping": "New Title", "year": 2023},
                {"genre": "Rock"},
            ),
        ]
    )
    def test_compatibility_with_modify_basic_field(
        self, initial_fields, commands, expected_fields, unchanged_fields
    ):
        """
        Test that multimodify command behaves the same as modify for basic field updates
        """
        item = self.add_item(**initial_fields)

        # Split command if it contains multiple operations
        self.run_command("multimodify", "-y", *commands)
        item.load()

        # Check expected changes
        for field, expected_value in expected_fields.items():
            assert getattr(item, field) == expected_value

        # Check unchanged fields
        for field, expected_value in unchanged_fields.items():
            assert getattr(item, field) == expected_value

    def test_compatibility_with_modify_query_behavior(self):
        """Test that multimodify command uses the same query behavior as modify"""
        # Add multiple items
        item1 = self.add_item(artist="Artist A", title="Song 1")
        item2 = self.add_item(artist="Artist B", title="Song 2")
        item3 = self.add_item(artist="Artist A", title="Song 3")

        # Use multimodify command with query (should behave like modify)
        self.run_command("multimodify", "-y", "artist:Artist A", "genre=Rock")

        # Reload items
        item1.load()
        item2.load()
        item3.load()

        # Only items matching the query should be modified
        assert item1.genre == "Rock"
        assert item2.genre == ""  # Should remain unchanged
        assert item3.genre == "Rock"

    @parameterized.expand(
        [
            # single_field_deletion
            (
                {"grouping": "Test Song", "genre": "Rock", "year": 2023},
                "genre!",
                {"genre": ""},
                {"grouping": "Test Song", "year": 2023},
            ),
            # multiple_field_deletions
            (
                {"grouping": "Test Song", "genre": "Rock", "year": 2023},
                "grouping! year!",
                {"grouping": "", "year": 0},
                {"genre": "Rock"},
            ),
        ]
    )
    def test_compatibility_with_modify_field_deletion(
        self, initial_fields, deletion_command, expected_deletions, unchanged_fields
    ):
        """Test that multimodify command supports field deletion like modify"""
        item = self.add_item(**initial_fields)

        # Split command if it contains multiple operations
        commands = deletion_command.split()
        self.run_command("multimodify", "-y", *commands)
        item.load()

        # Check deleted fields
        for field, expected_value in expected_deletions.items():
            assert getattr(item, field) == expected_value

        # Check unchanged fields
        for field, expected_value in unchanged_fields.items():
            assert getattr(item, field) == expected_value

    def test_compatibility_with_modify_mixed_operations(self):
        """Test that multimodify command supports mixed operations like modify"""
        self.enable_string_field()
        item = self.add_item(grouping="Old Artist", genre="Rock,Pop", year=2020)

        # Mix basic assignment, field deletion, and multimodify operations
        self.run_command(
            "multimodify", "-y", "grouping=New Artist", "year!", "genre+=Jazz"
        )
        item.load()
        assert item.grouping == "New Artist"
        assert item.year == 0
        assert item.genre == "Rock,Pop,Jazz"

    @parameterized.expand(
        [
            # write_nomove_options
            (["-y", "--write", "--nomove"], "grouping=New Title", "New Title"),
            # nowrite_option
            (["-y", "--nowrite"], "grouping=New Title", "New Title"),
        ]
    )
    def test_compatibility_with_modify_command_options(
        self, options, command, expected_value
    ):
        """Test that multimodify command accepts the same options as modify command"""
        # Extract field name from command for item creation
        field_name = command.split("=")[0]
        item = self.add_item(**{field_name: "Old Value"})

        # Run command with options
        self.run_command("multimodify", *options, command)
        item.load()

        # Check that the field was updated
        assert getattr(item, field_name) == expected_value

    def test_compatibility_with_modify_no_matching_items(self):
        """Test that multimodify command has similar error handling to modify"""
        with pytest.raises(beets.ui.UserError, match=r"No matching items found\."):
            self.run_command("multimodify")

        with pytest.raises(beets.ui.UserError, match=r"No matching items found\."):
            self.run_command("multimodify", "-y", "nonexistent:query", "title=Test")
