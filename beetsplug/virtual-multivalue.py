import mediafile
from beets import library, ui
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, decargs, print_
from beets.ui.commands import _do_query, print_and_modify
from beets.util import functemplate


class MultiCommand:

    @classmethod
    def get_command(cls) -> Subcommand:
        multi_command = Subcommand("multi", help="do something super")
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

        multi_command.func = cls.multi

        return multi_command

    @classmethod
    def parse_args(cls, args) -> tuple[list, list, list]:
        query = []
        adds = []
        removes = []
        for arg in args:
            if "+=" in arg and ":" not in arg.split("+=", 1)[0]:
                key, val = arg.split("+=", 1)
                adds.append((key, val))
            elif "-=" in arg and ":" not in arg.split("-=", 1)[0]:
                key, val = arg.split("-=", 1)
                removes.append((key, val))
            else:
                query.append(arg)

        return query, adds, removes

    @classmethod
    def update_multivalue(cls, value: str, adds: list, removes: list) -> str:
        """
        Add all elements in ``adds`` and remove all elements in ``removes`` to
        ``value``.
        """
        multi_values = value.split(";")
        for a in adds:
            if a not in multi_values:
                multi_values.append(a)
        for r in removes:
            try:
                multi_values.pop(multi_values.index(r))
            except ValueError:
                pass

        return ";".join(multi_values)

    @classmethod
    def modify_multi_items(
        cls, lib, adds, removes, query, write, move, album, confirm, inherit
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

            obj_mods = {
                key: model_cls._parse(
                    key,
                    cls.update_multivalue(
                        obj.get(key, ""),
                        [obj.evaluate_template(a) for a in templates[key]["adds"]],
                        [obj.evaluate_template(r) for r in templates[key]["removes"]],
                    ),
                )
                for key in templates.keys()
            }
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

            changed, _ = zip(
                *ui.input_select_objects(
                    "Really modify%s" % extra,
                    zip(changed, changes),
                    lambda o, om: print_and_modify(o, om, []),
                )
            )

        # Apply changes to database and files
        with lib.transaction():
            for obj in changed:
                obj.try_sync(write, move, inherit)

    @classmethod
    def multi(cls, lib, opts, args):
        """CLI entry"""
        query, adds, removes = cls.parse_args(decargs(args))

        cls.modify_multi_items(
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


class VirtualMultiValue(BeetsPlugin):
    def __init__(self):
        super().__init__()
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

    def commands(self):
        return [MultiCommand.get_command()]
