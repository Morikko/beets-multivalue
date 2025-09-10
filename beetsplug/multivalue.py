from typing import Iterable, Literal, Optional, Type

import mediafile
from beets import dbcore, library, plugins, ui
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, UserError, decargs, print_
from beets.ui.commands import _do_query, print_and_modify
from beets.util import functemplate

SearchTuple = tuple[str, Type[dbcore.query.FieldQuery]]

example_usage = """
Examples:
beet multimodify grouping+="Hard Rock" <query>
beet mmod genre+="Classic Rock" genre-="Hard Rock" <query>
beet mmod genre+="Classic Rock" genre-="Hard Rock" year! title="Best song"
beet multimodify grouping+="Rock" <query>
beet multimodify grouping+=~rock <query>
beet multimodify artists+=#Éric <query>
beet multimodify grouping-="Blues" <query>
beet multimodify grouping-=~rock <query>
beet multimodify artists-=#Eric <query>
beet multimodify artists-=:E?ic <query>
beet mm 'genre-=:Rock.+' genre+=Rock <query>
"""


class MultiValuePlugin(BeetsPlugin):
    """
    Add a modify command with add/remove values in multivalue fields
    """

    REAL_MULTIVALUE_FIELDS = {
        "artists",
        "albumartists",
        "artists_sort",
        "artists_credit",
        "albumartists_sort",
        "albumartists_credit",
        "mb_artistids",
        "mb_albumartistids",
    }

    def __init__(self):
        super().__init__()
        self.config.add({"string_fields": {}, "fix_media_fields": False})
        self.init_fix_media_field()

    @property
    def string_multivalue_fields(self):
        return self.config["string_fields"].get(dict)

    def get_prefixes(self):
        prefixes = {
            ":": dbcore.query.RegexpQuery,
            "~": dbcore.query.StringQuery,
        }
        prefixes.update(plugins.queries())
        return prefixes

    def commands(self):
        return [self.get_command()]

    def get_command(self) -> Subcommand:
        multi_command = Subcommand(
            "multimodify",
            help="modify command with add/remove in multi-value tags",
            aliases=("mmod", "mm"),
        )
        multi_command.parser.usage += example_usage
        multi_command.parser.add_option(
            "-m",
            "--move",
            action="store_true",
            dest="move",
            help="move files in the library directory",
        )
        multi_command.parser.add_option(
            "-M",
            "--nomove",
            action="store_false",
            dest="move",
            help="don't move files in library",
        )
        multi_command.parser.add_option(
            "-w",
            "--write",
            action="store_true",
            default=None,
            help="write new metadata to files' tags (default)",
        )
        multi_command.parser.add_option(
            "-W",
            "--nowrite",
            action="store_false",
            dest="write",
            help="don't write metadata (opposite of -w)",
        )
        multi_command.parser.add_album_option()
        multi_command.parser.add_format_option(target="item")
        multi_command.parser.add_option(
            "-y", "--yes", action="store_true", help="skip confirmation"
        )
        multi_command.parser.add_option(
            "-I",
            "--noinherit",
            action="store_false",
            dest="inherit",
            default=True,
            help="when modifying albums, don't also change item data",
        )

        multi_command.func = self.multi

        return multi_command

    def parse_key_val(
        self, value: str, action: Literal["+", "-"]
    ) -> Optional[tuple[str, str, Type[dbcore.query.FieldQuery]]]:
        """
        Check if the value is doing an add or remove.
        """
        full_action = f"{action}="
        if full_action not in value:
            return None

        key, val = value.split(full_action, 1)

        if ":" in key:
            return None

        if (
            key not in self.string_multivalue_fields
            and key not in self.REAL_MULTIVALUE_FIELDS
        ):
            raise UserError(f"'{key}' is not a declared multivalue field")

        for pre, query_class in self.get_prefixes().items():
            if val.startswith(pre):
                if action == "+" and issubclass(query_class, dbcore.query.RegexpQuery):
                    raise UserError("Regex is not supported when adding a value")
                return key, val[len(pre) :], query_class

        # Exact match by default
        return (key, val, dbcore.query.MatchQuery)

    def parse_args(self, args) -> tuple[list, dict, list, list, list]:
        query = []
        mods = {}
        dels = []
        adds = []
        removes = []
        for arg in args:

            added_action = self.parse_key_val(arg, "+")
            if added_action:
                adds.append(added_action)
                continue

            removed_action = self.parse_key_val(arg, "-")
            if removed_action:
                removes.append(removed_action)
                continue

            if arg.endswith("!") and "=" not in arg and ":" not in arg:
                dels.append(arg[:-1])  # Strip trailing !.
            elif "=" in arg and ":" not in arg.split("=", 1)[0]:
                key, val = arg.split("=", 1)
                mods[key] = val
            else:
                query.append(arg)

        return query, mods, dels, adds, removes

    def update_string_multivalue(
        self,
        value: str,
        assignment: Optional[str],
        adds: Iterable[SearchTuple],
        removes: Iterable[SearchTuple],
        separator: str,
    ) -> str:
        """
        Add all elements in ``adds`` and remove all elements in ``removes`` to
        ``value``.
        """
        # 1/ Assignment
        base_value = assignment if assignment is not None else value

        multi_values = base_value.split(separator) if len(base_value) > 0 else []

        # 2/ Remove
        for pattern, query in removes:
            # Necessary to support regex. Convert the str to a regex.
            pattern = query(pattern=pattern, field_name="").pattern
            multi_values = [
                value for value in multi_values if not query.value_match(pattern, value)
            ]

        # 3/ Add
        for pattern, query in adds:
            is_matching = False
            for value in multi_values:
                if query.value_match(pattern, value):
                    is_matching = True

            if not is_matching:
                multi_values.append(pattern)

        return separator.join(multi_values)

    def update_list_multivalue(
        self,
        values: list[str],
        assignment: Optional[str],
        adds: Iterable[SearchTuple],
        removes: Iterable[SearchTuple],
    ) -> list[str]:
        """
        Add all elements in ``adds`` and remove all elements in ``removes`` to
        ``values``.
        """
        # 1/ Assignment
        if assignment == "":
            multi_values = []
        elif assignment:
            multi_values = assignment.split(r"\␀")
        else:
            multi_values = values.copy()

        # 2/ Remove
        for pattern, query in removes:
            pattern = query(pattern=pattern, field_name="").pattern
            multi_values = [
                value for value in multi_values if not query.value_match(pattern, value)
            ]

        # 3/ Add
        for pattern, query in adds:
            is_matching = False
            for value in multi_values:
                if query.value_match(pattern, value):
                    is_matching = True

            if not is_matching:
                multi_values.append(pattern)

        return multi_values

    def evaluate_value_template(self, obj, value: Optional[str]) -> Optional[str]:
        return obj.evaluate_template(value) if value is not None else None

    def evaluate_iter_template(self, obj, values: Iterable[SearchTuple]):
        return [(obj.evaluate_template(a), query) for a, query in values]

    def get_default_template(self) -> dict:
        return {
            "set": None,
            "adds": [],
            "removes": [],
        }

    def modify_multi_items(
        self,
        lib,
        mods,
        dels,
        adds,
        removes,
        query,
        write,
        move,
        album,
        confirm,
        inherit,
    ):
        """
        Manage the multi values update, mostly influenced by modify command

        Order of application
        # 1/ Assignment
        # 2/ Remove
        # 3/ Add
        # 4/ Del
        """
        # Parse key=value specifications into a dictionary.
        model_cls = library.Album if album else library.Item

        # Get the items to modify.
        items, albums = _do_query(lib, query, album, False)
        objs = albums if album else items

        # Apply changes *temporarily*, preview them, and collect modified
        # objects.
        print_("Modifying {} {}s.".format(len(objs), "album" if album else "item"))
        changed = []
        changes = []

        templates = {}
        for key, value, query in adds:
            if key not in templates:
                templates[key] = self.get_default_template()
            templates[key]["adds"].append((functemplate.template(value), query))

        for key, value, query in removes:
            if key not in templates:
                templates[key] = self.get_default_template()
            templates[key]["removes"].append((functemplate.template(value), query))

        for key, value in mods.items():
            if key not in templates:
                templates[key] = self.get_default_template()
            templates[key]["set"] = functemplate.template(value)

        for obj in objs:
            obj_mods = {}
            for key in templates.keys():
                if key in self.string_multivalue_fields:
                    obj_mods[key] = model_cls._parse(
                        key,
                        self.update_string_multivalue(
                            obj.get(key, ""),
                            self.evaluate_value_template(obj, templates[key]["set"]),
                            self.evaluate_iter_template(obj, templates[key]["adds"]),
                            self.evaluate_iter_template(obj, templates[key]["removes"]),
                            self.string_multivalue_fields[key],
                        ),
                    )
                elif key in self.REAL_MULTIVALUE_FIELDS:
                    obj_mods[key] = self.update_list_multivalue(
                        obj.get(key, []),
                        self.evaluate_value_template(obj, templates[key]["set"]),
                        self.evaluate_iter_template(obj, templates[key]["adds"]),
                        self.evaluate_iter_template(obj, templates[key]["removes"]),
                    )
                else:
                    obj_mods[key] = model_cls._parse(
                        key, obj.evaluate_template(templates[key]["set"])
                    )

            if print_and_modify(obj, obj_mods, dels) and obj not in changed:
                changed.append(obj)
                changes.append(obj_mods)

        # Still something to do?
        if not changed:
            print_("No changes to make.")
            return

        # Confirm action.
        if confirm:
            if write and move:
                extra = ", move and write tags"
            elif write:
                extra = " and write tags"
            elif move:
                extra = " and move"
            else:
                extra = ""

            selected_objects = ui.input_select_objects(
                "Really modify%s" % extra,
                zip(changed, changes),
                lambda o, om: print_and_modify(o, om, dels),
            )

            if not selected_objects:
                return

            changed, _ = zip(*selected_objects)

        # Apply changes to database and files
        with lib.transaction():
            for obj in changed:
                obj.try_sync(write, move, inherit)

    def multi(self, lib, opts, args):
        """CLI entry"""
        query, mods, dels, adds, removes = self.parse_args(decargs(args))

        self.modify_multi_items(
            lib,
            mods,
            dels,
            adds,
            removes,
            query,
            ui.should_write(opts.write),
            ui.should_move(opts.move),
            opts.album,
            not opts.yes,
            opts.inherit,
        )

    ##
    # FixMediaField
    ##

    def init_fix_media_field(self):
        """
        "grouping" field was using the wrong fields for MP3 and ASF storage. Add the
        "work" field as well as it was those fields used.
        """
        if self.config["fix_media_fields"].get(bool):
            self.fix_grouping_work_field()

    def fix_grouping_work_field(self):
        grouping_field = mediafile.MediaField(
            mediafile.MP3StorageStyle("GRP1"),
            mediafile.MP4StorageStyle("\xa9grp"),
            mediafile.StorageStyle("GROUPING"),
        )
        # Overwrite to avoid: ValueError: property "grouping" already exists on
        # MediaFile
        mediafile.MediaFile.grouping = grouping_field
        work_field = mediafile.MediaField(
            mediafile.MP3StorageStyle("TIT1"),
            mediafile.MP4StorageStyle("\xa9wrk"),
            mediafile.StorageStyle("WORK"),
            mediafile.ASFStorageStyle("WM/ContentGroupDescription"),
        )
        self.add_media_field("work", work_field)
