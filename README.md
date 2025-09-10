# Multi-value Plugin

Multi-values on a tag is useful to provide different and independent information
belonging to the same context.

This plugin provides a boosted modify command to also add/remove values in
multi-value tag. It can also fix `grouping` field and add `work` field.

## Beet official list tags

A few fields already support native multi-values separated with `\␀`. Those are
always available in the command without a configuration change. The current
fields are:

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
explicitly defined in the configuration with the expected separator:

```yaml
multivalue:
  string_fields:
    grouping: ";"
    genre: ","
```

## Multi Modify Command

### Usage

```shell
# Initial: genre: Rock

# Add a value
beet multimodify grouping+="Hard Rock" <query>
# genre: Rock,Hard Rock

# Add and remove values
beet mmod genre+="Classic Rock" genre-="Hard Rock" <query>
# genre: Rock,Classic Rock

# Original modify command still applies
beet mmod genre+="Classic Rock" genre-="Hard Rock" year! title="Best song"

# Adding the same value is detected and avoided. By default, exact match is applied.
# It is easy to remember, there is the "=", the same used in a regular query.
# Initial: genre: Rock
beet multimodify grouping+="Rock" <query>
# genre: Rock

# For case insensitivity, add "~" as in a regular query.
beet multimodify grouping+=~rock <query>
# genre: Rock

# It is also possible to use the ones from a plugin by adding the equivalent prefix.
# For example with bareasc set to the prefix "#".
# Initial: artists: [Eric]
beet multimodify artists+=#Éric <query>
# no change

# The same work for removing

# Initial: genre: Rock
beet multimodify grouping-="Blues" <query>
# No change

# For case insensitivity, add "~" as in a regular query
# Initial: genre: Rock
beet multimodify grouping-=~rock <query>
# genre: ""

# For bareasc set to the prefix "#"
# Initial: artists: [Éric]
beet multimodify artists-=#Eric <query>
# artists: []

# Removing is also supporting Regex
# Initial: artists: [Eric]
beet multimodify artists-=:E?ic <query>
# artists: []

# Adding can not support regex as else the regex itself would be added. 
# If you want to harmonize the data, you may remove and add at the same time.
# Initial: genre: Rock&Roll
beet multimodify 'genre-=:Rock.+' genre+=Rock <query>
# genre: Rock

# Order of execution
# genre: original
beet mm genre+=base genre-=base genre=base,pivot
# genre: pivot,base

# Deletion always win
beet mm genre! genre+=base genre-=base genre=base,pivot
# genre:

# Reset field first
beet mm  genre= genre+=new genre-=new2
# genre: new,new2
```

The command is influenced by the `modify` one and provides the same flags. By
default, a confirmation after showing the diff is requested and highly
recommended to avoid any data loss.

### Order of execution

1. Direct assignment are always run first: `genre=Rock`. If multiple assignments
   on the same field are written, the last one win.

2. Values are removed: `genre-=Rock`. It allows to do some pre-cleaning before
   adding values in the same run. Always with capital R: `genre-=rock
   genre+=Rock`. Values are removed in order from the CLI `genre-=Rock
   genre-=Classic`: first `Rock` then `Classic`.

3. Values are added in order from the CLI `genre+=Rock genre+=Classic`: first
   `Rock` then `Classic`.

The order above is not impacted if the CLI options are unordered: `genre+=Rock
genre=Blues` would still do the assignment first.

The deletion `genre!` is always run last whatever its position. It keeps the
compatibility with the actual `modify` command behavior. To reset a field before
adding values, one must use `genre= genre+=Rock` or `artists= artists+=Eric`.

### Performance

To optimize performance and avoid iterating over a lot of data, the query should
prune items as much as possible.

```sh
# Only iterate over items without the Rock word in genre
beet multimodify genre+=Rock '^genre:Rock'

# Only iterate over items with the Rock word in genre
beet multimodify genre-=Rock 'genre:Rock'
```

### Limitation

A/ Sub-Optimal Diff

The diff may be sub-optimal as it does not know about the separator. In the
following example "Classic Rock" is not highlighted continuously although the
final change is still accurate: `genre: Hard Rock,**Classic** Rock,**Rock** ->
Hard Rock,Rock`.

B/ Relation to the original modify command

The modify command has been "copied" and upstream changes won't apply without a
port in this plugin.

C/ No order support

I have no need for ordering the values in the tag, as a result, it is always
added last.

## Grouping/Work fields

`mediafile` the file level library is using the wrong tag name for MP3 (see
[issue](https://github.com/beetbox/mediafile/issues/15)). As the `grouping`
field was my first motivation to use string multi-value, this plugin is also
able to fix the field.

The changes are:
- `grouping`: for MP3 is changed to `GRP1` and ASF does not support it as
  without a defined value
- `work` field is added for MP3 (`TIT1`), MP4 (`@wrk`), Vorbis (`WORK`) and ASF
  (`WM/ContentGroupDescription`). The values for MP3 and ASF were previously
  assigned to `grouping`.

The tags are chosen from [Kid3
table](https://kid3.sourceforge.io/kid3_en.html#frame-list).

It is disabled by default so to enable it:

```yaml
multivalue:
  fix_media_fields: true
```

It is required to make beets read the tags from the file again as else the kept
values in DB are the old ones from the potential wrong fields:

```shell
beet update -F work -F grouping
```

WARNING: As the `work` field was not saved to the file previously, by reading
from the files, it may remove all the `work` fetched from Musicbrainz and only
stored in the DB.

