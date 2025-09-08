# Multi-value

Multi-values on a tag is useful to provide different and independent information
belonging to the same context.

This plugin:
- Add a command to add/remove values in a multi-value tag
- Fix `grouping` field and add `work` field (Optional)

## Beet official list tags

A few fields already support native multivalue separated with `\␀`. Those are
always available in the command without configuration change. The current fields
are:

- artists
- albumartists
- artists_sort
- artists_credit
- albumartists_sort
- albumartists_credit
- mb_artistids
- mb_albumartistids

## String multi-value tags

Some fields do not support multi-values yet like
[genre](https://github.com/beetbox/beets/pull/5426) or some may never support it
as not a "standard" like `grouping`.

An example could be to add multiple genres separated by a comma: `Rock,Hard Rock`

Some external tools also supports custom separator splitting like
[navidrome](https://www.navidrome.org/docs/usage/customtags/#changing-separators)
since v0.55.0.

By default, no field is considered a string multi-value. Each one must be
explicitly defined in the configuration with the requested separator:

```yaml
multivalue:
  string_fields:
    grouping: ";"
    genre: ","
```

# Modify Command

It is possible to add or remove value:

```shell
# Initial: genre: Rock
beet multivalue grouping+="Hard Rock" <query>
# genre: Rock,Hard Rock
beet multi genre+="Classic Rock" genre-="Hard Rock" genre-="Blues" <query>
# genre: Rock,Classic Rock

# Original modify command still applies
beet multi genre+="Classic Rock" genre-="Hard Rock" year! title="Best sont"
```

The command is influenced by the modify one and provide the same flags. By
default, a confirmation after showing the diff is requested and highly
recommended to avoid any data loss.

The diff may be sub-optimal as it does not know about the separator. In the
following example "Classic Rock" is not highlighted continously although the
final change is still accurate: `genre: Hard Rock,**Classic** Rock,**Rock** ->
Hard Rock,Rock`.

The modify command has been "copied" and upstream changes won't apply without a
port in this plugin.


# Grouping/Work fields

https://github.com/beetbox/mediafile/issues/15 `mediafile` the file level
library is using the wrong tag name for MP3. As a result, the common work is
visible. As grouping field was my first motivation to use string multi-value,
this plugin is also able to fix the field.

In such case:
- `grouping`: for MP3 is `GRP1` and ASF is removed as without a value
- `work` field is added for MP3 (`TIT1`), MP4 (`@wrk`), Vorbis (`WORK`) and ASF
  (`WM/ContentGroupDescription`). The value for MP3 and ASF was previously
  assigned to `grouping`.

The tags are chosen from [Kid3
table](https://kid3.sourceforge.io/kid3_en.html#frame-list).

To enable it:

```yaml
multivalue:
  fix_media_fields: true
```

It is required to make beets read the tags from the file again as else the kept
value in DB is the old one from a potential wrong fields:

```shell
beet update -F work -F grouping
```

WARNING: As the work was not saved to the file previously, by reading from the
files it may remove all the "work" fetched from Musicbrainz and only stored in
the DB.

