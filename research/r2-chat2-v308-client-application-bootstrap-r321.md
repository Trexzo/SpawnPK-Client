# Chat 2 — exact-v308 client application bootstrap R321

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/p/a` -> `CLIENT_CLASS_000740` -> `ClientApplicationBootstrap`
- `rs/p/b` -> `CLIENT_CLASS_000741` -> `ClientApplicationModule`
- review: `SEMREVIEW_0D295A9FD0A31BA94A66`

## ClientApplicationBootstrap

The static startup path creates the root Guice injector from exactly one module,
`rs/p/b`, then:

1. resolves `rs/gui/Launcher`;
2. installs it as the active Launcher singleton;
3. resolves `rs/p/a`;
4. invokes the bootstrap instance lifecycle.

The root Injector is retained statically and exposed to other live subsystems.

The instance startup lifecycle initializes and starts the injected application services:

- configuration/service manager;
- plugin manager/load path;
- UI manager;
- EventBus registrations;
- plugin activation;
- UI activation;
- final client event bridge initialization.

Static application paths are also owned here:

- `~/.spawnpk-data`
- `~/.spawnpk-data/plugins`
- `~/.spawnpk-data/screenshots`

This fixes the role as client-application bootstrap/composition infrastructure.

## ClientApplicationModule

`rs/p/b` extends `com.google.inject.AbstractModule` and is supplied directly to the
root `Guice.createInjector` call.

Its bindings include:

- named `developerMode`;
- named `safeMode`;
- concrete `Client` instance;
- `ScheduledExecutorService`;
- core plugin/config/UI services;
- serializer instance;
- primary `EventBus`;
- named `Deferred EventBus` -> `DeferredEventBus`.

It also exposes one `@Provides @Singleton` service resolved from the configuration/service
manager.

## Boundary

The names describe exact-v308 architectural roles. They do not claim original stripped
source identifiers and remain non-canonical Chat 2 research.
