import java.io.ByteArrayOutputStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import rs.Client;
import rs.definitions.IdentityKit;
import rs.definitions.SequenceDefinition;
import rs.io.Packet;
import rs.model.Model;
import rs.model.Player;

/**
 * Source-built, offline opcode-81 integration regression.
 * Uses actual Client.method1850, Packet, Player and Model classes; no sockets.
 * A zero-equipment appearance is a parser fixture, NEVER a gameplay avatar.
 * Requires a local X display because Client extends java.applet.Applet.
 */
public final class R266RealClientPlayerSyncRegression {
    private static int checks;

    private static void check(boolean ok, String reason) {
        if (!ok) throw new AssertionError(reason);
        checks++;
    }

    private static void word(ByteArrayOutputStream b, int n) {
        b.write((n >>> 8) & 255);
        b.write(n & 255);
    }

    private static byte[] appearance(String username) {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        for (int i = 0; i < 5; i++) b.write(0); // gender and 4 icons
        word(b, 0); // rank; default donatorRights=false
        for (int i = 0; i < 12; i++) b.write(0); // intentionally no body kits
        b.write(0); // cosmetic absent
        for (int i = 0; i < 5; i++) b.write(0); // colors
        for (int i = 0; i < 7; i++) word(b, 65535); // unknown animations
        b.write(0); // no name prefix
        byte[] name = (username + "\n").getBytes(StandardCharsets.ISO_8859_1);
        b.write(name, 0, name.length);
        b.write(3); // combat level
        word(b, 0); // skill level
        b.write(0); // status byte
        b.write(0); // no custom colors
        return b.toByteArray();
    }

    private static byte[] maskedUpdate(String username) {
        byte[] body = appearance(username);
        check(body.length < 256, "appearance exceeds length byte");
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        for (int value : new int[]{0x80, 0x1f, 0xfc, 0x10, (-body.length) & 255}) b.write(value);
        b.write(body, 0, body.length);
        return b.toByteArray();
    }

    private static void feed(Method method, Client client, byte[] bytes) throws Exception {
        method.invoke(client, bytes.length, new Packet(bytes));
    }

    public static void main(String[] args) throws Exception {
        check(!Boolean.getBoolean("java.awt.headless"), "client needs a local X display");
        Client client = new Client();
        Player player = new Player();
        Client.localPlayer = Client.players[2047] = player;
        check(!player.hasAppearance, "new local player already initialized");

        Method handle = Client.class.getDeclaredMethod("method1850", int.class, Packet.class);
        handle.setAccessible(true);
        byte[] first = maskedUpdate("LocalTest");
        check(first.length == 60, "R265 frame changed");
        feed(handle, client, first);
        check(Client.localPlayer == player, "local player identity changed");
        check(player.hasAppearance, "Client opcode-81 did not set hasAppearance");
        check("LocalTest".equals(player.username), "Client opcode-81 lost name");
        for (int slot : player.equipment) check(slot == 0, "unexpected equipment");

        // Self movement=none; retained-player count=0; added-player sentinel=2047.
        byte[] repeat = {0x00, 0x7f, (byte)0xf0};
        feed(handle, client, repeat);
        check(Client.localPlayer == player, "local player replaced on no-mask sync");
        check(player.hasAppearance && "LocalTest".equals(player.username),
                "appearance lost on no-mask sync");

        byte[] second = maskedUpdate("LocalTwo");
        feed(handle, client, second);
        check("LocalTwo".equals(player.username), "appearance replacement failed");
        check(player.hasAppearance, "appearance flag lost");

        // Incomplete wire frame must not report a successful parse.
        byte[] cut = {(byte)0x80, 0x1f, (byte)0xfc, 0x10, (byte)0xc9, 0, 0};
        boolean refused = false;
        try {
            feed(handle, client, cut);
        } catch (InvocationTargetException expected) {
            refused = expected.getCause() instanceof RuntimeException
                    || expected.getCause() instanceof Error;
        }
        check(refused, "truncated appearance frame accepted");

        // This demonstrates precisely why the R265 zero-equipment fixture
        // is not a visible avatar. No authentic model/kit files are invented.
        SequenceDefinition.cache = new SequenceDefinition[20000];
        IdentityKit.cache = new IdentityKit[0];
        Model model = player.method279(true);
        check(model != null, "empty appearance yielded null model");
        check(model.vertexCount == 0, "empty equipment unexpectedly has vertices");
        check(model.faceCount == 0, "empty equipment unexpectedly has faces");
        System.out.println("R266_CLIENT_81_FULL_DISPATCH_PASS checks=" + checks
                + " firstBytes=" + first.length + " repeatBytes=" + repeat.length
                + " secondBytes=" + second.length);
        System.out.println("R266_PLAYER_MESH_GATE_CONFIRMED vertices=" + model.vertexCount
                + " faces=" + model.faceCount + " REAL_KIT_ASSETS_REQUIRED");
    }
}
