import java.awt.Robot;
import java.awt.Rectangle;
import java.awt.event.InputEvent;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.io.File;
/** One native AWT Robot instance, two genuinely picked distinct scene objects. */
public final class R279TwoActionRobot {
    private static void click(Robot robot,int x,int y,boolean right) {
        robot.mouseMove(x,y); robot.delay(370);
        int button = right ? InputEvent.BUTTON3_DOWN_MASK : InputEvent.BUTTON1_DOWN_MASK;
        robot.mousePress(button); robot.delay(130); robot.mouseRelease(button); robot.delay(400);
    }
    private static void shot(Robot robot,String path)throws Exception {
        BufferedImage frame=robot.createScreenCapture(new Rectangle(0,0,1400,900));
        if(!ImageIO.write(frame,"PNG",new File(path)))throw new IllegalStateException("PNG image encoder absent");
    }
    public static void main(String[] args)throws Exception {
        if(args.length!=1)throw new IllegalArgumentException("expected output directory only");
        File dir=new File(args[0]);if(!dir.isDirectory())throw new IllegalArgumentException("output must exist");
        Robot r=new Robot();r.setAutoWaitForIdle(false);
        click(r,460,270,true);
        shot(r,new File(dir,"R279_compost_context_menu.png").getPath());
        System.out.println("R279_COMPOST_REAL_RIGHT_CLICK x=460 y=270");
        click(r,420,299,false);
        System.out.println("R279_COMPOST_REAL_SEARCH_CLICK x=420 y=299");
        r.delay(1800);
        click(r,514,318,true);
        shot(r,new File(dir,"R279_chest_context_menu.png").getPath());
        System.out.println("R279_CHEST_REAL_RIGHT_CLICK x=514 y=318");
        click(r,511,349,false);
        System.out.println("R279_CHEST_REAL_SEARCH_CLICK x=511 y=349");
        r.delay(900);
        shot(r,new File(dir,"R279_after_two_actions.png").getPath());
        System.out.println("R279_TWO_DISTINCT_GUI_MENU_ACTIONS_AWT_PASS");
    }
}
