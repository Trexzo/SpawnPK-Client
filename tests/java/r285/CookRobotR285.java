import java.awt.Robot;
import java.awt.Rectangle;
import java.awt.event.InputEvent;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
public final class CookRobotR285 {
  private static void snap(Robot r,File dir,String name)throws Exception {
    File tmp=new File(dir,name+".partial.png");
    BufferedImage img=r.createScreenCapture(new Rectangle(0,0,1400,900));
    if(!ImageIO.write(img,"png",tmp)) throw new Exception("PNG encoder absent");
    Files.move(tmp.toPath(),new File(dir,name).toPath(),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
  }
  private static void click(Robot r,int x,int y,int mask)throws Exception{
    r.mouseMove(x,y);r.delay(330);r.mousePress(mask);r.delay(125);r.mouseRelease(mask);r.delay(380);
  }
  public static void main(String[]args)throws Exception{
    if(args.length!=1)throw new IllegalArgumentException("expected output directory");
    File dir=new File(args[0]);if(!dir.isDirectory())throw new IllegalArgumentException("output directory absent");
    Robot r=new Robot();r.setAutoWaitForIdle(false);
    click(r,514,318,InputEvent.BUTTON3_DOWN_MASK);
    snap(r,dir,"R285_Cook_context.png");
    System.out.println("R285_ACTUAL_OSRS_COOK_CONTEXT_MENU_CAPTURED");
    click(r,483,349,InputEvent.BUTTON1_DOWN_MASK);
    System.out.println("R285_ACTUAL_OSRS_COOK_OPTION_CLICKED");
    r.delay(900);snap(r,dir,"R285_after_Cook.png");
    System.out.println("R285_ROBOT_CLICK_AND_ATOMIC_SCREENSHOTS_PASS");
  }
}
