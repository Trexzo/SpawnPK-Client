# Chat 2 — source-proven plugin framework R411

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/a` / 000853 -> `Plugin`
- `rs/s/b` / 000859 -> `PluginClassLoader`
- `rs/s/c` / 000885 -> `PluginDependencies`
- `rs/s/d` / 000895 -> `PluginDependency`
- `rs/s/e` / 000898 -> `PluginDescriptor`
- `rs/s/f` / 000905 -> `PluginInstantiationException`
- `rs/s/g` / 000912 -> `PluginManager`
- `rs/s/h` / 000915 -> `RuneLiteConfig`
- review: `SEMREVIEW_DAD50216A5C66F3A1F2B`

The recovered source map supplies all eight exact source identities. Exact v308 independently
corroborates the Guice Plugin base, URLClassLoader-backed plugin classloader, dependency and
descriptor annotations, dedicated instantiation exception, live manager orchestration and
root RuneLite configuration interface.

The manager's live dependencies include EventBus, scheduler and ConfigManager, tying this
family directly to R321 ClientApplicationBootstrap.

R411 remains non-canonical semantic research only.
