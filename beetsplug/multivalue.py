from typing import Optional, Union

import mediafile
from beets import library, ui
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, UserError, decargs, print_
from beets.ui.commands import _do_query, print_and_modify
from beets.util import functemplate


class MultiValuePlugin(BeetsPlugin):
    """
    Add a command to add/remove value in a multivalue field string.
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
        self.config.add({"string_fields": {}})

    @property
    def string_multivalue_fields(self):
        return self.config["string_fields"].get(dict)

    def commands(self):
        return [self.get_command()]

    def get_command(self) -> Subcommand:
        multi_command = Subcommand(
            "multivalue",
            help="Add/Remove values in a multivalue field string",
            aliases=("multi"),
        )
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

    def parse_key_val(self, value: str, action: str) -> Optional[tuple[str, str]]:
        if action in value and ":" not in value.split(action, 1)[0]:
            key, val = value.split(action, 1)
            if (
                key not in self.string_multivalue_fields
                and key not in self.REAL_MULTIVALUE_FIELDS
            ):
                raise UserError(f"'{key}' is not a declared multivalue field")
            return (key, val)
        else:
            return None

    def parse_args(self, args) -> tuple[list, list, list]:
        query = []
        adds = []
        removes = []
        for arg in args:

            added_action = self.parse_key_val(arg, "+=")
            if added_action:
                adds.append(added_action)
                continue

            removed_action = self.parse_key_val(arg, "-=")
            if removed_action:
                removes.append(removed_action)
                continue

            query.append(arg)

        return query, adds, removes

    def update_string_multivalue(
        self, value: str, adds: list, removes: list, separator: str
    ) -> str:
        """
        Add all elements in ``adds`` and remove all elements in ``removes`` to
        ``value``.
        """
        multi_values = value.split(separator)
        for a in adds:
            if a not in multi_values:
                multi_values.append(a)
        for r in removes:
            try:
                multi_values.pop(multi_values.index(r))
            except ValueError:
                pass

        return separator.join(multi_values)

    def update_list_multivalue(self, values: list, adds: list, removes: list) -> list:
        """
        Add all elements in ``adds`` and remove all elements in ``removes`` to
        ``values``.
        """
        multi_values = [v for v in values if v not in removes]
        for a in adds:
            if a not in multi_values:
                multi_values.append(a)

        return multi_values

    def modify_multi_items(
        self, lib, adds, removes, query, write, move, album, confirm, inherit
    ):
        """Manage the multi values update, mostly influenced by modify command"""
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
        for key, value in adds:
            if key not in templates:
                templates[key] = {
                    "adds": [],
                    "removes": [],
                }
            templates[key]["adds"].append(functemplate.template(value))

        for key, value in removes:
            if key not in templates:
                templates[key] = {
                    "adds": [],
                    "removes": [],
                }
            templates[key]["removes"].append(functemplate.template(value))

        for obj in objs:
            obj_mods = {}
            for key in templates.keys():
                if key in self.string_multivalue_fields:
                    obj_mods[key] = model_cls._parse(
                        key,
                        self.update_string_multivalue(
                            obj.get(key, ""),
                            [obj.evaluate_template(a) for a in templates[key]["adds"]],
                            [
                                obj.evaluate_template(r)
                                for r in templates[key]["removes"]
                            ],
                            self.string_multivalue_fields[key],
                        ),
                    )
                else:
                    obj_mods[key] = self.update_list_multivalue(
                        obj.get(key, []),
                        [obj.evaluate_template(a) for a in templates[key]["adds"]],
                        [obj.evaluate_template(r) for r in templates[key]["removes"]],
                    )

            if print_and_modify(obj, obj_mods, []) and obj not in changed:
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
                lambda o, om: print_and_modify(o, om, []),
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
        query, adds, removes = self.parse_args(decargs(args))

        self.modify_multi_items(
            lib,
            adds,
            removes,
            query,
            ui.should_write(opts.write),
            ui.should_move(opts.move),
            opts.album,
            not opts.yes,
            opts.inherit,
        )


class FixMediaField(BeetsPlugin):
    """
    "grouping" field was using the wrong fields for MP3 and ASF storage. Add the
    "work" field as well as it was those fields used.
    """

    def __init__(self):
        super().__init__()
        self.config.add({"fix_media_fields": False})
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
