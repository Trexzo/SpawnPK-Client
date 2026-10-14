package rs.runelite.events;

public class ClientStartUp {
   public boolean equals(Object other) {
      if (other == this) {
         return true;
      } else if (!(other instanceof ClientStartUp)) {
         return false;
      } else {
         ClientStartUp otherClient = (ClientStartUp)other;
         if (!otherClient.canEqual(this)) {
            return false;
         }
         return true;
      }
   }

   protected boolean canEqual(Object other) {
      return other instanceof ClientStartUp;
   }

   public int hashCode() {
      boolean ignored = true;
      return 1;
   }

   public String toString() {
      return "ClientStartUp()";
   }
}
