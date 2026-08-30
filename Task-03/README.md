# The Grand Line Restoration Initiative

the first step is definitely looking at git history.

```
git branch -a
```

only one branch.

i run 
```
git log --oneline --all --decorate --graph
```

everything commited in one go. i don't need to look through commits and branches for this one.

i run `tree` to get a birds eye view of the dir structure. four projects in the archives, `alabaster`, `east-blue`, `reverse-mountain`, `whiskey-peak`. i'll get to those last.

i read all the docs, tools, `Cargo.toml`, `Cargo.toml.bak`, `src/main.rs`.

`Cargo.toml.bak` refers to 

```
navnet-core = { path = "navnet-core" }
```
but there's no `navnet-core` in root dir. a remnant from a previous architecture? i leave it as is for now.

the scripts in the `tools` folder indicate the four archives are supposed to be left as is, and that im not expected to rebuild everything into a new application.

i start with `./archives/index.md`, then explore all four archives, just to get a lay of the land. i look at their `Cargo.toml` files, docs, logs, source folders, configs, tests, scripts. i'm starting to get an idea of what i have here.

i run 

```
cargo test --workspace --all-targets
```

i get one failure,

```
failures:

---- asset_directory_is_expected_in_config_tree stdout ----

thread 'asset_directory_is_expected_in_config_tree' (72204) panicked at archives/reverse-mountain/tests/integration.rs:22:5:
expected configured asset directory to exist
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace


failures:
    asset_directory_is_expected_in_config_tree

```
which was expected as per documentation in the reverse-mountain archive. it explicitly menstions the asset-path issue. the other archives don't have this problem, and include code to create the assets dir if missing.

next i run 
```
cargo fmt --all -- --check
``` 

i find a handful of formatting errors. so i run `cargo fmt --all` to format the files. 

while im at it, i run 

```
cargo clippy --workspace --all-targets -- -D warnings
```

two straightforward fixes. i need to investigate how `to_str` is being called before i can safely change that one.

since it seems to be preserving a legacy output, im not going to change to FromStr lest i introduce unexpected behaviour. i'll just change the name of the function to `parse`. since its only used in two locations on the same page and nowhere else, this should be fine. 

i run clippy again. reformat a nested if, remove a few default declarations. i'm left with this one:

![IMAGE](./clippy_warning_data_dir.png)  

data_dir isnt being used anywhere, but i dont think its safe to delete it, as is seems to be an expected part of the structure, and i can see it in the other archives as well. it's referenced in the logs as well. incomplete migration?  i'll put a warning that this should be expected there. `#[expect(dead_code)]` for now.

i run clippy again. an unused import in `alabaster/tests/integration.rs`. i remove it.

i run all the following commands and get an all clear.
```
cargo fmt --all
cargo fmt --all -- --check
cargo test --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
```
about all i can do.








