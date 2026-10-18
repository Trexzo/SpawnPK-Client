import java.awt.Robot;
import java.awt.Rectangle;
import java.awt.event.InputEvent;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.io.File;
public final class R280InteractiveRobot {
  private static void click(Robot robot,int x,int y,boolean right){
    robot.mouseMove(x,y);robot.delay(330);
    int mask=right?InputEvent.BUTTON3_DOWN_MASK:InputEvent.BUTTON1_DOWN_MASK;
    robot.mousePress(mask);robot.delay(100);robot.mouseRelease(mask);robot.delay(340);
  }
  private static void snap(Robot r,File d,String name)throws Exception{
    File tmp=new File(d,name+".partial");
    if(!ImageIO.write(r.createScreenCapture(new Rectangle(0,0,1400,900)),"png",tmp))throw new Exception("PNG writer missing");
    java.nio.file.Files.move(tmp.toPath(),new File(d,name).toPath(),java.nio.file.StandardCopyOption.ATOMIC_MOVE,java.nio.file.StandardCopyOption.REPLACE_EXISTING);
  }
  public static void main(String[]args)throws Exception{
    if(args.length!=1)throw new IllegalArgumentException("expected output dir");
    File dest=new File(args[0]);Robot r=new Robot();r.setAutoWaitForIdle(false);
    click(r,460,270,true);snap(r,dest,"R280_compost_menu.png");
    click(r,420,299,false);System.out.println("R280_OBJECT_SEARCH_COMPOST_CLICK_SENT");
    r.delay(1050);
    click(r,514,318,true);snap(r,dest,"R280_chest_menu.png");
    click(r,511,349,false);System.out.println("R280_OBJECT_SEARCH_CHEST_CLICK_SENT");
    r.delay(1350);
    click(r,310,315,false);System.out.println("R280_REAL_VIEWPORT_WALK_CLICK_SENT x=310 y=315");
    r.delay(1850);snap(r,dest,"R280_after_walk.png");
    System.out.println("R280_GUI_TWO_OBJECTS_AND_WALK_ROBOT_DONE");
  }
}
