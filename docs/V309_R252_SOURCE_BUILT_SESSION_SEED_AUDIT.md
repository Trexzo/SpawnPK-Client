# R252 local session-seed recovery (actual R247 source audit)

R247 `rs/io/Packet.java` `encryptRsa()` does NOT perform RSA modular exponentiation: it reads block bytes into Java BigInteger and writes `toByteArray()` with a one-byte length. The resulting test-only login frame is recoverable without a private RSA key.

`Client.login()` constructs the inner block with marker 10 then four 32-bit seed words: two random words, high and low halves of 64-bit server challenge. It then writes the remaining login fields. The outer frame begins opcode 16/18; body contains 255, short 317, a flag, nine 32-bit cache revisions, then the length-prefixed block. It seeds outgoing ISAAC with the original four words, incoming ISAAC with each word +50 (modulo 2^32).

A private bounded login-frame parser validates opcode, exact challenge and declared lengths, and avoids saving credentials. Five independent unit tests PASS. Private ZIP SHA256 `f641c56780b08601a851b290f9b134892d54c912d8b06df43956979ec44f0010`. This result is **limited to the reconstructed client code** and does not establish original server encryption or actual world initialization.

Next: compare matching Java `Class257` ISAAC streams, then send ISAAC-framed region/identity packets to the actual client in a controlled loopback test and capture post-initialization behavior. No actual R252 client runtime test, native Windows test, or gameplay proof. PR #1084 remains draft.