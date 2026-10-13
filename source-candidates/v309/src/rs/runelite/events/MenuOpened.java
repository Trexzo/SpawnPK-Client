package rs.runelite.events;

public class MenuOpened {
   public boolean equals(Object other) {
      if (other == this) {
         return true;
      } else if (!(other instanceof MenuOpened)) {
         return false;
      } else {
         MenuOpened otherClient = (MenuOpened)other;
         if (!otherClient.canEqual(this)) {
            return false;
         }
         return true;
      }
   }

   protected boolean canEqual(Object other) {
      return other instanceof MenuOpened;
   }

   public int hashCode() {
      boolean ignored = true;
      return 1;
   }

   public String toString() {
      return "MenuOpened()";
   }
}
