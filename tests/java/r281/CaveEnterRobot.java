import java.awt.Robot;
import java.awt.Rectangle;
import java.awt.event.InputEvent;
import javax.imageio.ImageIO;
import java.nio.file.*;
public final class CaveEnterRobot {
 static void click(Robot r,int x,int y,boolean right){r.mouseMove(x,y);r.delay(300);int b=right?InputEvent.BUTTON3_DOWN_MASK:InputEvent.BUTTON1_DOWN_MASK;r.mousePress(b);r.delay(100);r.mouseRelease(b);r.delay(360);}
 static void shot(Robot r,Path d,String name)throws Exception{Path t=d.resolve(name+".partial");ImageIO.write(r.createScreenCapture(new Rectangle(0,0,1400,900)),"PNG",t.toFile());Files.move(t,d.resolve(name+".png"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}
 public static void main(String[]a)throws Exception{
  Path d=Paths.get(a[0]);Robot r=new Robot();r.setAutoWaitForIdle(false);r.delay(6000);
  click(r,480,285,true);shot(r,d,"R281_cave_context");System.out.println("R281_REAL_CAVE_ENTER_CONTEXT_MENU_OPENED");
  click(r,420,314,false);System.out.println("R281_REAL_CAVE_ENTER_FIRST_OPTION_SELECTED");
  r.delay(1200);shot(r,d,"R281_after_cave_enter");
  click(r,310,315,false);System.out.println("R281_REAL_WALK_AFTER_CAVE_CLICK_SENT");
  r.delay(1700);shot(r,d,"R281_after_cave_walk");System.out.println("R281_CAVE_ROBOT_DONE");
 }
}
