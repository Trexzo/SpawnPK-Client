import java.awt.*;import java.awt.event.*;import javax.imageio.ImageIO;import java.io.File;
public class CookRobot {
 public static void main(String[]args)throws Exception {
  Robot r=new Robot();r.setAutoWaitForIdle(false);r.delay(4500);
  r.mouseMove(514,318);r.delay(400);r.mousePress(InputEvent.BUTTON3_DOWN_MASK);r.delay(120);r.mouseRelease(InputEvent.BUTTON3_DOWN_MASK);r.delay(430);
  ImageIO.write(r.createScreenCapture(new Rectangle(0,0,1400,900)),"PNG",new File(args[0],"R284_Cook_context.png"));
  System.out.println("R284_COOK_CONTEXT_MENU_OPENED");
  r.mouseMove(483,349);r.delay(420);r.mousePress(InputEvent.BUTTON1_DOWN_MASK);r.delay(150);r.mouseRelease(InputEvent.BUTTON1_DOWN_MASK);
  System.out.println("R284_ACTUAL_COOK_FIRST_OPTION_CLICKED");r.delay(1100);
  ImageIO.write(r.createScreenCapture(new Rectangle(0,0,1400,900)),"PNG",new File(args[0],"R284_after_Cook.png"));
 }
}
