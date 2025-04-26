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
